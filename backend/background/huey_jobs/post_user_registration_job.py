import asyncio
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from config.huey import huey
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from services.registration_service import RegistrationService
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("PostRegistrationJob")


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


async def post_registration_job_async(
    user_id: str,
):
    async with get_mongo_db() as db:
        registration_service = RegistrationService(db=db, logger=logger)
        await registration_service.process_new_registration(user_id=user_id)


@huey.task()
def post_registration_job(
    user_id: str,
):
    logger.info(f"Starting post registration job for user id {user_id}")
    try:
        asyncio.run(post_registration_job_async(user_id))
        logger.info(f"Finished post registration job for user id {user_id}")
    except Exception as e:
        logger.error(e)
        logger.exception(f"Error in post registration job for user id {user_id}")
        raise  # Re-raise the exception so Huey marks the task as failed
