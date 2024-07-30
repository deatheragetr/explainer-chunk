from typing import List, TypedDict, Optional, Annotated, Dict
import aiohttp
from aiohttp import ClientSession
from bs4 import BeautifulSoup
import logging
from contextlib import asynccontextmanager
from config.s3 import s3_client
from config.environment import WasabiSettings
from config.redis import host as redis_host, port as redis_port, db as redis_db, Redis
import json
import asyncio
from urllib.parse import urljoin, urlparse
import os
import mimetypes

from config.huey import huey
from huey.api import Task as HueyTask

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="capture_website.log",
)
logger = logging.getLogger(__name__)


# S3 configuration
wasabiSettings = WasabiSettings()
S3_BUCKET = wasabiSettings.wasabi_document_bucket


# Status update stream data
class ProgressData(TypedDict, total=False):
    presigned_url: Annotated[Optional[str], "S3 Presigned URL"]
    file_type: Annotated[Optional[str], "File Type"]


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


async def fetch_and_store_resource(
    session: ClientSession, url: str, base_url: str, capture_id: str
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

        s3_key = f"captures/{capture_id}/{file_name}"
        s3_client.put_object(
            Bucket=S3_BUCKET, Key=s3_key, Body=content, ContentType=content_type
        )

        return s3_client.generate_presigned_url(
            "get_object", Params={"Bucket": S3_BUCKET, "Key": s3_key}, ExpiresIn=3600
        )
    except Exception as e:
        print(f"Error fetching resource {url}: {str(e)}")
        logger.error(f"Error fetching resource {url}: {str(e)}")

        return None


async def update_progress(
    redis_client: Redis,  # type: Redis[bytes]
    task_id: str,
    status: str,
    progress: Optional[float] = None,
    payload: Optional[ProgressData] = ProgressData(),
):
    await redis_client.publish(
        "capture_website_task",
        json.dumps(
            {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "payload": payload,
            }
        ),
    )


@asynccontextmanager
async def get_session():
    async with ClientSession() as session:
        yield session


@asynccontextmanager
async def get_redis_client():
    client = Redis(host=redis_host, port=redis_port, db=redis_db)
    try:
        yield client
    finally:
        await client.close()


async def capture_html(
    redis_client: Redis,
    session: ClientSession,
    url: str,
    response: aiohttp.ClientResponse,
    capture_id: str,
):
    try:
        html_content = await response.text()

        soup = BeautifulSoup(html_content, "html.parser")

        # Process CSS files
        await update_progress(redis_client, capture_id, "PROGRESS", 30)
        css_tasks: List[asyncio.Task[str | None]] = []

        for tag in soup.find_all("link", rel="stylesheet"):
            if tag.has_attr("href"):
                task = asyncio.create_task(
                    fetch_and_store_resource(session, tag["href"], url, capture_id)
                )
                css_tasks.append(task)
        css_results = await asyncio.gather(*css_tasks)
        for tag, new_url in zip(soup.find_all("link", rel="stylesheet"), css_results):
            if new_url:
                tag["href"] = new_url

        # Process JavaScript files
        await update_progress(redis_client, capture_id, "PROGRESS", 50)
        js_tasks: List[asyncio.Task[str | None]] = []

        for tag in soup.find_all("script", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(session, tag["src"], url, capture_id)
            )
            js_tasks.append(task)
        js_results = await asyncio.gather(*js_tasks)
        for tag, new_url in zip(soup.find_all("script", src=True), js_results):
            if new_url:
                tag["src"] = new_url

        # Process images
        await update_progress(redis_client, capture_id, "PROGRESS", 70)
        img_tasks: List[asyncio.Task[str | None]] = []

        for tag in soup.find_all("img", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(session, tag["src"], url, capture_id)
            )
            img_tasks.append(task)
        img_results = await asyncio.gather(*img_tasks)
        for tag, new_url in zip(soup.find_all("img", src=True), img_results):
            if new_url:
                tag["src"] = new_url

        # Store the modified HTML
        await update_progress(redis_client, capture_id, "PROGRESS", 90)
        html_key = f"captures/{capture_id}/index.html"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=html_key,
            Body=str(soup),
            ContentType="text/html",
        )

        capture_url: str = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": html_key},
            ExpiresIn=3600,
        )

        await update_progress(
            redis_client,
            capture_id,
            "COMPLETE",
            100,
            ProgressData(
                presigned_url=capture_url, file_type=supported_file_types["html"]
            ),
        )
        return {
            "status": "Website captured successfully",
            "presigned_url": capture_url,
        }

    except Exception as e:
        await update_progress(redis_client, capture_id, "ERROR")
        print("ERROR: IN CAPTURE WEB SITE: ", str(e))
        print("ERROR: IN CAPTURE WEB SITE: ", e.__traceback__)
        logger.error(f"Task failed for URL: {url}, Task ID: {capture_id}")
        logger.error("Exception details:", exc_info=True)


async def capture_non_html(
    redis_client: Redis,
    session: ClientSession,
    url: str,
    response: aiohttp.ClientResponse,
    capture_id: str,
    normalized_file_type: str,
):
    try:
        content = await response.read()
        content_type = response.headers.get(
            "content-type", "application/octet-stream"
        ).split(";")[0]
        file_name = os.path.basename(urlparse(url).path) or "downloaded_file"

        s3_key = f"captures/{capture_id}/{file_name}"
        s3_client.put_object(
            Bucket=S3_BUCKET, Key=s3_key, Body=content, ContentType=content_type
        )

        capture_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=3600,
        )

        await update_progress(
            redis_client,
            capture_id,
            "COMPLETE",
            100,
            ProgressData(presigned_url=capture_url, file_type=normalized_file_type),
        )
        return {
            "status": "File downloaded and stored successfully",
            "presigned_url": capture_url,
        }

    except Exception as e:
        await update_progress(redis_client, capture_id, "ERROR")
        logger.error(f"Direct download failed for URL: {url}, Task ID: {capture_id}")
        logger.error("Exception details:", exc_info=True)
        return {"status": "Error", "message": str(e)}


def normalize_file_type(content_type: str, file_extension: str) -> str:
    # Remove any parameters from the content type (e.g., charset)
    content_type = content_type.split(";")[0].lower()

    # Mapping of content types and file extensions to normalized types

    type_mapping = {
        # PDF
        "application/pdf": supported_file_types["pdf"],
        ".pdf": supported_file_types["pdf"],
        # EPUB
        "application/epub+zip": supported_file_types["epub"],
        ".epub": supported_file_types["epub"],
        # JSON
        "application/json": supported_file_types["json"],
        ".json": supported_file_types["json"],
        # Markdown
        "text/markdown": supported_file_types["markdown"],
        ".md": supported_file_types["markdown"],
        ".markdown": supported_file_types["markdown"],
        # Plain text
        "text/plain": supported_file_types["text"],
        ".txt": supported_file_types["text"],
        # Excel/csv
        "text/csv": supported_file_types["csv"],
        ".csv": supported_file_types["csv"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": supported_file_types[
            "excel"
        ],
        ".xlsx": supported_file_types["excel"],
        # HTML (for completeness)
        "text/html": supported_file_types["html"],
        ".html": supported_file_types["html"],
        ".htm": supported_file_types["html"],
    }

    # Try to match content type first, then file extension
    normalized_type = type_mapping.get(content_type) or type_mapping.get(
        file_extension.lower()
    )

    # If no match found, return 'unknown'
    return normalized_type or "unknown"


async def async_capture(url: str, capture_id: str):
    async with get_redis_client() as redis_client, get_session() as session:
        try:
            await update_progress(redis_client, capture_id, "STARTED")

            # Fetch main HTML
            await update_progress(redis_client, capture_id, "PROGRESS", 10)
            async with session.get(url) as response:

                content_type = (
                    response.headers.get("content-type", "").split(";")[0].lower()
                )
                file_extension = mimetypes.guess_extension(content_type) or ""

                normalized_type = normalize_file_type(content_type, file_extension)

                if normalized_type == supported_file_types["html"]:
                    result = await capture_html(
                        redis_client, session, url, response, capture_id
                    )
                elif normalized_type in supported_file_types.values():
                    result = await capture_non_html(
                        redis_client,
                        session,
                        url,
                        response,
                        capture_id,
                        normalized_type,
                    )
                else:
                    await update_progress(redis_client, capture_id, "ERROR")
                    return {
                        "status": "Error",
                        "message": f"Unsupported file type: {normalized_type}",
                    }

            return result
        except Exception as e:
            await update_progress(redis_client, capture_id, "ERROR")
            print("ERROR: IN CAPTURE WEB SITE: ", str(e))
            logger.error(f"Async_capture failed for URL: {url}, Task ID: {capture_id}")
            logger.error("Exception details:", exc_info=True)
            return {"status": "Error", "message": str(e)}


@huey.task(context=True)
def capture_website(url: str, task: Optional[HueyTask] = None):
    if task:
        # This is the task execution path
        capture_id: str = task.id
        return asyncio.run(async_capture(url, capture_id))
    else:
        # This is the task enqueue path
        # We don't have a task ID yet, so we just return
        # The actual execution will happen later
        return
