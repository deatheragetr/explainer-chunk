import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from config.huey import huey
from config.redis import RedisPool, RedisType
from config.ai_models import DEFAULT_MODEL_CONFIGS, ModelPairConfig
from config.environment import PineconeSettings, OpenAISettings
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from services.ai_explain_text_service import AIExplainTextService
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


async def async_explain_text(
    document_upload_id: str,
    highlighted_text: str,
    model_config: ModelPairConfig,
):
    async with get_redis_client() as redis_client, get_mongo_db() as db:
        progress_updater = ProgressUpdater(
            redis_client, document_upload_id, "explain_text_task"
        )
        ai_explain_text_service = AIExplainTextService(
            openai_api_key=open_ai_settings.openai_api_key,
            model_pair_config=model_config,
            progress_updater=progress_updater,
            db=db,
        )
        try:
            await ai_explain_text_service.explain_text(
                document_upload_id, highlighted_text, model_config
            )
            logger.info(
                f"Finished explaining text section with document_upload_id={document_upload_id} for model={model_config['chat_model']['model_name']}"
            )
        finally:
            ai_explain_text_service.openai_assistant_service.client.close()


@huey.task()
def explain_text(
    document_upload_id: str,
    highlighted_text: str,
    model_name: str = "gpt-4-mini",
):
    logger.info(
        f"Starting explain text task for document_upload_id={document_upload_id} for model={model_name}"
    )
    try:
        model_pair_config = DEFAULT_MODEL_CONFIGS[model_name]

        asyncio.run(
            async_explain_text(document_upload_id, highlighted_text, model_pair_config)
        )

        logger.info(
            f"Finished explain text task document_id={document_upload_id} for model={model_name}"
        )
    except Exception as e:
        logger.exception(
            f"Error in explaining text for document_id={document_upload_id} for model={model_name}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
