import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from config.huey import huey
from config.redis import RedisPool, RedisType
from config.ai_models import DEFAULT_MODEL_CONFIGS, ModelPairConfig
from config.environment import PineconeSettings, OpenAISettings
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
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
    pool = RedisPool()
    try:
        client: RedisType = await pool.get_client()
        yield client
    finally:
        await pool.close()


# Not ideal, but this is the only apparant way to avoid event loop is closed errors
@asynccontextmanager
async def get_mongo_db() -> AsyncGenerator[TypedAsyncIOMotorDatabase, None]:
    mongo_manager = MongoManager[TypedAsyncIOMotorDatabase](mongo_settings)
    await mongo_manager.connect()
    assert mongo_manager.db is not None
    try:
        yield mongo_manager.db
    finally:
        await mongo_manager.close()


async def async_summarize_document(
    document_upload_id: str,
    model_config: ModelPairConfig,
):
    async with get_redis_client() as redis_client, get_mongo_db() as db:
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
            # await ai_summary_service.most_advanced_summarize(document_upload_id)
            # await ai_summary_service.basic_summarize_text(document_upload_id)

            await ai_summary_service.map_reduce_summarize(document_upload_id, db)
            # await ai_summary_service.sequential_summarize(document_upload_id, db)
            logger.info(
                f"Finished summarizing document with document_upload_id={document_upload_id} for model={model_config['chat_model']['model_name']}"
            )
        finally:
            await ai_summary_service.openai_client.close()


@huey.task()
def summarize_document(
    document_upload_id: str,
    model_name: str = "gpt-4-mini",
):
    logger.info(
        f"Starting summarize document for document_upload_id={document_upload_id} for model={model_name}"
    )
    try:
        model_pair_config = DEFAULT_MODEL_CONFIGS[model_name]

        asyncio.run(async_summarize_document(document_upload_id, model_pair_config))

        logger.info(
            f"Finished summarizing for document_id={document_upload_id} for model={model_name}"
        )
    except Exception as e:
        logger.exception(
            f"Error in summarizing document for document_id={document_upload_id} for model={model_name}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
