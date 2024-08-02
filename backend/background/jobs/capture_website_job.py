import asyncio
from typing import List, TypedDict, Optional, Annotated, AsyncGenerator, Any
import aiohttp
from bson import ObjectId
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import logging
from contextlib import asynccontextmanager
import json
from urllib.parse import urljoin, urlparse
import os
import mimetypes
from config.huey import huey
from config.s3 import s3_client
from config.environment import S3Settings, MongoSettings
from config.redis import Redis, RedisType
from config.mongo import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from db.models.document_uploads import (
    MongoDocumentUpload,
    create_mongo_file_details,
    generate_s3_key_for_file,
    generate_s3_key_for_web_capture,
    generate_s3_url,
    AllowedFolders,
    AllowedS3Buckets,
    SourceType,
    S3Bucket
)


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="capture_website.log",
)
logger = logging.getLogger(__name__)

# S3 configuration
s3_settings = S3Settings()
S3_HOST = s3_settings.s3_host

PUBLIC_BUCKET = AllowedS3Buckets.PUBLIC_BUCKET.value
DOCUMENT_UPLOAD_BUCKET = AllowedS3Buckets.DOCUMENT_UPLOADS.value
WEB_CAPTURES_FOLDER = AllowedFolders.WEB_CAPTURES.value
DOCUMENT_UPLOADS_FOLDER = AllowedFolders.DOCUMENT_UPLOADS.value

# Status update stream data
class ProgressData(TypedDict, total=False):
    presigned_url: Annotated[Optional[str], "S3 Presigned URL"]
    file_type: Annotated[Optional[str], "File Type"]
    file_name: Annotated[Optional[str], "File Name"]
    document_upload_id: Annotated[Optional[str], "Document Upload ID"]
    url_friendly_file_name: Annotated[Optional[str], "URL-friendly version of the file name"]

supported_file_types = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
    "json": "application/json",
    "markdown": "text/markdown",
    "text": "text/plain",
    "csv": "text/csv",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "html": "text/html",
}

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
async def get_mongo_client(collection_name: str) -> AsyncGenerator[AsyncIOMotorCollection[MongoDocumentUpload], None]:
    mongo_settings = MongoSettings()
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_settings.mongo_url)
    db: AsyncIOMotorDatabase[MongoDocumentUpload] = client[mongo_settings.mongo_db]
    try:
        yield db[collection_name]
    finally:
        client.close()

async def fetch_and_store_resource(
    session: ClientSession, url: str, base_url: str, document_upload_id: str, bucket: S3Bucket
):
    try:
        full_url = urljoin(base_url, url)
        parsed_url = urlparse(full_url)
        file_name = os.path.basename(parsed_url.path) or "index.html"

        async with session.get(full_url) as response:
            content = await response.read()

        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        ).split(";")[0]

        s3_key = generate_s3_key_for_web_capture(
            folder=AllowedFolders.WEB_CAPTURES,
            object_id=ObjectId(document_upload_id),
            file_name=file_name,
        )
        s3_client.put_object(
            Bucket=bucket.value,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        s3_url = generate_s3_url(S3_HOST, bucket, s3_key)
        return s3_url
    except Exception as e:
        logger.error(f"Error fetching resource {url}: {str(e)}")
        return None


# RedisType = Union[Redis, 'Redis[bytes]']



async def update_progress(
    redis_client: RedisType,
    document_upload_id: str,
    status: str,
    progress: Optional[float] = None,
    payload: Optional[ProgressData] = None,
):

    await redis_client.publish(
        "capture_website_task",
        json.dumps(
            {
                "connection_id": document_upload_id,
                "status": status,
                "progress": progress,
                "payload": payload or {},
            }
        ),
    )

async def capture_html(
    redis_client: RedisType,
    session: ClientSession,
    mongo_collection: AsyncIOMotorCollection[MongoDocumentUpload],
    url: str,
    response: aiohttp.ClientResponse,
    document_upload_id: str,
):
    try:
        html_content = await response.text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Process CSS files
        await update_progress(redis_client, document_upload_id, "PROGRESS", 30)
        css_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("link", rel="stylesheet"):
            if tag.has_attr("href"):
                task = asyncio.create_task(
                    fetch_and_store_resource(session, tag["href"], url, document_upload_id, AllowedS3Buckets.PUBLIC_BUCKET)
                )
                css_tasks.append(task)
        css_results = await asyncio.gather(*css_tasks)
        for tag, new_url in zip(soup.find_all("link", rel="stylesheet"), css_results):
            if new_url:
                tag["href"] = new_url

        # Process JavaScript files
        await update_progress(redis_client, document_upload_id, "PROGRESS", 50)
        js_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("script", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(session, tag["src"], url, document_upload_id, AllowedS3Buckets.PUBLIC_BUCKET)
            )
            js_tasks.append(task)
        js_results = await asyncio.gather(*js_tasks)
        for tag, new_url in zip(soup.find_all("script", src=True), js_results):
            if new_url:
                tag["src"] = new_url

        # Process images
        await update_progress(redis_client, document_upload_id, "PROGRESS", 70)
        img_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("img", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(session, tag["src"], url, document_upload_id, AllowedS3Buckets.PUBLIC_BUCKET)
            )
            img_tasks.append(task)
        img_results = await asyncio.gather(*img_tasks)
        for tag, new_url in zip(soup.find_all("img", src=True), img_results):
            if new_url:
                tag["src"] = new_url

        # Store the modified HTML
        await update_progress(redis_client, document_upload_id, "PROGRESS", 90)
        html_key = generate_s3_key_for_web_capture(
            folder=AllowedFolders.WEB_CAPTURES,
            object_id=ObjectId(document_upload_id),
            file_name="index.html",
        )
        s3_client.put_object(
            Bucket=PUBLIC_BUCKET,
            Key=html_key,
            Body=str(soup),
            ContentType="text/html",
        )

        s3_url = generate_s3_url(S3_HOST, AllowedS3Buckets.PUBLIC_BUCKET, html_key)
        mongo_file_details = create_mongo_file_details(
            file_name="index.html",
            file_type=supported_file_types["html"],
            file_key=html_key,
            s3_url=s3_url,
            s3_bucket=PUBLIC_BUCKET,
            source=SourceType.WEB,
            source_url=url,
        )

        document = MongoDocumentUpload(
            _id=ObjectId(document_upload_id), file_details=mongo_file_details
        )

        await mongo_collection.update_one(
            {"_id": ObjectId(document_upload_id)},
            {"$set": document},
            upsert=True,
        )

        await update_progress(
            redis_client,
            document_upload_id,
            "COMPLETE",
            100,
            ProgressData(
                presigned_url=s3_url,
                file_type=supported_file_types["html"],
                file_name="index.html",
                document_upload_id=document_upload_id,
                url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            ),
        )
        return {
            "status": "Website captured successfully",
            "presigned_url": s3_url,
        }

    except Exception as e:
        await update_progress(redis_client, document_upload_id, "ERROR")
        logger.error(f"Task failed for URL: {url}, Task ID: {document_upload_id}")
        logger.error(e)
        logger.exception("Exception details:")
        raise

async def capture_non_html(
    redis_client: RedisType,
    session: ClientSession,
    mongo_collection: AsyncIOMotorCollection[MongoDocumentUpload],
    url: str,
    response: aiohttp.ClientResponse,
    document_upload_id: str,
    normalized_file_type: str,
):
    try:
        await update_progress(redis_client, document_upload_id, "PROGRESS", 50)
        content = await response.read()
        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        ).split(";")[0]
        file_name = os.path.basename(urlparse(url).path) or "downloaded_file"

        s3_key = generate_s3_key_for_file(
            folder=AllowedFolders.DOCUMENT_UPLOADS,
            object_id=ObjectId(document_upload_id),
            file_name=file_name,
        )

        s3_client.put_object(
            Bucket=DOCUMENT_UPLOAD_BUCKET,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        await update_progress(redis_client, document_upload_id, "PROGRESS", 75)

        capture_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": DOCUMENT_UPLOAD_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )

        s3_url = generate_s3_url(S3_HOST, AllowedS3Buckets.DOCUMENT_UPLOADS, s3_key)

        await update_progress(redis_client, document_upload_id, "PROGRESS", 85)
        mongo_file_details = create_mongo_file_details(
            file_name=file_name,
            file_type=normalized_file_type,
            file_key=s3_key,
            s3_url=s3_url,
            s3_bucket=DOCUMENT_UPLOAD_BUCKET,
            source=SourceType.WEB,
            source_url=url,
        )

        document = MongoDocumentUpload(
            _id=ObjectId(document_upload_id), file_details=mongo_file_details
        )

        await mongo_collection.update_one(
            {"_id": ObjectId(document_upload_id)},
            {"$set": document},
            upsert=True,
        )

        await update_progress(
            redis_client,
            document_upload_id,
            "COMPLETE",
            100,
            ProgressData(
                presigned_url=capture_url,
                file_type=normalized_file_type,
                file_name=file_name,
                document_upload_id=document_upload_id,
                url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            ),
        )

        return {
            "status": "File downloaded and stored successfully",
            "presigned_url": capture_url,
        }

    except Exception as e:
        await update_progress(redis_client, document_upload_id, "ERROR")
        logger.error(e)
        logger.error(f"Direct download failed for URL: {url}, Task ID: {document_upload_id}")
        logger.exception("Exception details:")
        raise

def normalize_file_type(content_type: str, file_extension: str) -> str:
    content_type = content_type.split(";")[0].lower()
    type_mapping = {
        "application/pdf": supported_file_types["pdf"],
        ".pdf": supported_file_types["pdf"],
        "application/epub+zip": supported_file_types["epub"],
        ".epub": supported_file_types["epub"],
        "application/json": supported_file_types["json"],
        ".json": supported_file_types["json"],
        "text/markdown": supported_file_types["markdown"],
        ".md": supported_file_types["markdown"],
        ".markdown": supported_file_types["markdown"],
        "text/plain": supported_file_types["text"],
        ".txt": supported_file_types["text"],
        "text/csv": supported_file_types["csv"],
        ".csv": supported_file_types["csv"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": supported_file_types["excel"],
        ".xlsx": supported_file_types["excel"],
        "text/html": supported_file_types["html"],
        ".html": supported_file_types["html"],
        ".htm": supported_file_types["html"],
    }
    return type_mapping.get(content_type) or type_mapping.get(file_extension.lower()) or "unknown"

async def async_capture(url: str, document_upload_id: str):
    async with get_redis_client() as redis_client, get_session() as session, get_mongo_client("document_uploads") as mongo_collection:
        try:
            await update_progress(redis_client, document_upload_id, "STARTED")
            await update_progress(redis_client, document_upload_id, "PROGRESS", 10)
            
            async with session.get(url) as response:
                content_type = response.headers.get("content-type", "").split(";")[0].lower()
                file_extension = mimetypes.guess_extension(content_type) or ""

                normalized_type = normalize_file_type(content_type, file_extension)

                if normalized_type == supported_file_types["html"]:
                    result = await capture_html(
                        redis_client, session, mongo_collection, url, response, document_upload_id
                    )
                elif normalized_type in supported_file_types.values():
                    result = await capture_non_html(
                        redis_client,
                        session,
                        mongo_collection,
                        url,
                        response,
                        document_upload_id,
                        normalized_type,
                    )
                else:
                    await update_progress(redis_client, document_upload_id, "ERROR")
                    return {
                        "status": "Error",
                        "message": f"Unsupported file type: {normalized_type}",
                    }

            return result
        except Exception as e:
            await update_progress(redis_client, document_upload_id, "ERROR")
            logger.error(f"Async_capture failed for URL: {url}, Task ID: {document_upload_id}")
            logger.exception("Exception details:")
            return {"status": "Error", "message": str(e)}

@huey.task()
def capture_website(url: str, document_upload_id: str):
    logger.info(f"Starting capture_website task: URL={url}, ID={document_upload_id}")
    try:
        asyncio.run(async_capture(url, document_upload_id))
        logger.info(f"Finished capture_website task: URL={url}, ID={document_upload_id}")
    except Exception:
        logger.exception(f"Error in capture_website task: URL={url}, ID={document_upload_id}")
        raise  # Re-raise the exception so Huey marks the task as failed


# Usage example (not part of the task, just for illustration):
# result = capture_website(url, document_upload_id)