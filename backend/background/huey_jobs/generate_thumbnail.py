import asyncio
from typing import AsyncGenerator
from config.huey import huey
from contextlib import asynccontextmanager
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from services.thumbnail_service import ThumbnailService
from config.logger import get_logger
from config.s3 import s3_client

logger = get_logger()


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


async def async_generate_thumbnail(document_id: str):
    async with get_mongo_db() as db:
        thumbnail_generator = ThumbnailService(
            s3_client=s3_client,
            db=db,
        )
        await thumbnail_generator.generate_and_store_thumbnail(document_id)


@huey.task()
def generate_thumbnail(document_id: str):
    logger.info(f"Queueing generate thumbnail for document_id={document_id}")
    try:

        # Create and run the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_generate_thumbnail(document_id))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

        logger.info(f"Finished generating thumbnail for document_id={document_id}")
    except Exception as e:
        logger.exception(
            f"Error in generating thumbnail for document_id={document_id}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
