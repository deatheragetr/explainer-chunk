import asyncio
from contextlib import asynccontextmanager
from config.huey import huey
from config.redis import Redis
from config.ai_models import DEFAULT_MODEL_CONFIGS, ModelPairConfig
from config.environment import PineconeSettings, OpenAISettings
from services.ai_summary_service import AISummaryService
from utils.progress_updater import ProgressUpdater

import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

pinecone_settings = PineconeSettings()
open_ai_settings = OpenAISettings()


@asynccontextmanager
async def get_redis_client():
    client = Redis(host="localhost", port=6379, db=0)
    try:
        yield client
    finally:
        await client.close()


async def async_summarize_document(
    document_upload_id: str, model_config: ModelPairConfig
):
    async with get_redis_client() as redis_client:
        progress_updater = ProgressUpdater(
            redis_client, document_upload_id, "summarize_document_task"
        )
        ai_summary_service = AISummaryService(
            openai_api_key=open_ai_settings.openai_api_key,
            pinecone_api_key=pinecone_settings.pinecone_api_key,
            model_pair_config=model_config,
            progress_updater=progress_updater,
        )
        try:
            await ai_summary_service.most_advanced_summarize(document_upload_id)
            # await ai_summary_service.basic_summarize_text(document_upload_id)
            logger.info(
                f"Finished summarizing document with document_upload_id={document_upload_id} for model={model_config['chat_model']['model_name']}"
            )
        finally:
            await ai_summary_service.openai_client.close()


@huey.task()
def summarize_document(document_upload_id: str, model_name: str = "gpt-4-mini"):
    logger.info(
        f"Starting summarize document for document_upload_id={document_upload_id} for model={model_name}"
    )
    try:
        model_pair_config = DEFAULT_MODEL_CONFIGS[model_name]

        # Create and run the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                async_summarize_document(document_upload_id, model_pair_config)
            )
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

        logger.info(
            f"Finished summarizing for document_id={document_upload_id} for model={model_name}"
        )
    except Exception as e:
        logger.exception(
            f"Error in summarizing document for document_id={document_upload_id} for model={model_name}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
