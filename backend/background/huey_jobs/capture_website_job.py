import asyncio
import logging
from aiohttp import ClientSession
import mimetypes
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Optional

from config.huey import huey
from config.redis import Redis
from config.mongo import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)
from db.models.document_uploads import MongoDocumentUpload
from config.environment import MongoSettings
from utils.progress_updater import ProgressUpdater
from utils.file_type_normalizer import normalize_file_type, supported_file_types
from services.html_web_capture import capture_html
from services.non_html_web_capture import capture_non_html
from background.huey_jobs.generate_thumbnail import generate_thumbnail

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="capture_website.log",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def get_session():
    async with ClientSession() as session:
        yield session


@asynccontextmanager
async def get_redis_client():
    client = Redis(host="localhost", port=6379, db=0)
    try:
        yield client
    finally:
        await client.close()


@asynccontextmanager
async def get_mongo_client(
    collection_name: str,
) -> AsyncGenerator[AsyncIOMotorCollection[MongoDocumentUpload], None]:
    mongo_settings = MongoSettings()
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_settings.mongo_url)
    db: AsyncIOMotorDatabase[MongoDocumentUpload] = client[mongo_settings.mongo_db]
    try:
        yield db[collection_name]
    finally:
        client.close()


async def async_capture(
    url: str, document_upload_id: str, user_id: str, directory_id: Optional[str] = None
):
    async with get_redis_client() as redis_client, get_session() as session, get_mongo_client(
        "document_uploads"
    ) as mongo_collection:
        progress_updater = ProgressUpdater(
            redis_client, document_upload_id, "capture_website_task"
        )
        try:
            await progress_updater.update(10, "STARTED")

            async with session.get(url) as response:
                content_type = (
                    response.headers.get("content-type", "").split(";")[0].lower()
                )
                file_extension = mimetypes.guess_extension(content_type) or ""

                normalized_type = normalize_file_type(content_type, file_extension)

                if normalized_type == supported_file_types["html"]:
                    result = await capture_html(
                        progress_updater,
                        session,
                        mongo_collection,
                        url,
                        response,
                        document_upload_id,
                        logger,
                        user_id,
                        directory_id,
                    )
                elif normalized_type in supported_file_types.values():
                    result = await capture_non_html(
                        progress_updater,
                        session,
                        mongo_collection,
                        url,
                        response,
                        document_upload_id,
                        normalized_type,
                        logger,
                        user_id,
                        directory_id,
                    )
                else:
                    await progress_updater.error()
                    return {
                        "status": "Error",
                        "message": f"Unsupported file type: {normalized_type}",
                    }

            generate_thumbnail(document_upload_id)
            return result
        except Exception as e:
            await progress_updater.error()
            logger.error(
                f"Async_capture failed for URL: {url}, Task ID: {document_upload_id}"
            )
            logger.exception("Exception details:")
            return {"status": "Error", "message": str(e)}


@huey.task()
def capture_website(
    url: str, document_upload_id: str, user_id: str, directory_id: Optional[str] = None
):
    logger.info(f"Starting capture_website task: URL={url}, ID={document_upload_id}")
    try:
        result = asyncio.run(
            async_capture(url, document_upload_id, user_id, directory_id)
        )
        logger.info(
            f"Finished capture_website task: URL={url}, ID={document_upload_id}"
        )
        return result
    except Exception:
        logger.exception(
            f"Error in capture_website task: URL={url}, ID={document_upload_id}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
