import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from config.huey import huey
from config.redis import RedisPool, RedisType
from config.ai_models import DEFAULT_MODEL_CONFIGS, ModelPairConfig
from config.environment import OpenAISettings
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from services.ai_chat_service import AIChatService
from utils.progress_updater import ProgressUpdater
from config.logger import get_logger

logger = get_logger()

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


async def async_chat_with_rag(
    document_upload_id: str,
    message_content: str,
    model_config: ModelPairConfig,
):
    async with get_redis_client() as redis_client, get_mongo_db() as db:
        progress_updater = ProgressUpdater(
            redis_client, document_upload_id, "chat_task"
        )

        ai_chat_service = AIChatService(
            openai_api_key=open_ai_settings.openai_api_key,
            model_pair_config=model_config,
            progress_updater=progress_updater,
            db=db,
        )
        try:
            await ai_chat_service.send_chat_message(document_upload_id, message_content)
            logger.info(
                f"Finished chat job with document_upload_id={document_upload_id} for model={model_config['chat_model']['model_name']}"
            )
        finally:
            ai_chat_service.openai_assistant_service.client.close()


@huey.task()
def chat_with_rag(
    document_upload_id: str,
    message_content: str,
    model_name: str = "gpt-4o-mini",
):
    logger.info(
        f"Starting chat task for document_upload_id={document_upload_id} for model={model_name}"
    )
    try:
        model_pair_config = DEFAULT_MODEL_CONFIGS[model_name]

        asyncio.run(
            async_chat_with_rag(document_upload_id, message_content, model_pair_config)
        )

        logger.info(
            f"Finished chat task document_id={document_upload_id} for model={model_name}"
        )
    except Exception as e:
        logger.exception(
            f"Error in chat task for document_id={document_upload_id} for model={model_name}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
