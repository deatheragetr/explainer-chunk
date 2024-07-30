from typing import List, TypedDict, Optional, Annotated
import aiohttp
from bs4 import BeautifulSoup
import logging
from contextlib import asynccontextmanager
from config.s3 import s3_client
from config.environment import WasabiSettings
from config.redis import redis_client_sync as redis_client
import json
import asyncio
from urllib.parse import urljoin, urlparse
import os

from config.huey import huey
from huey.api import Task as HueyTask

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="capture_website.log",
)
logger = logging.getLogger(__name__)


# S3 configuration
wasabiSettings = WasabiSettings()
S3_BUCKET = wasabiSettings.wasabi_document_bucket


async def fetch_and_store_resource(
    session: aiohttp.ClientSession, url: str, base_url: str, capture_id: str
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


class ProgressData(TypedDict, total=False):
    presigned_url: Annotated[Optional[str], "S3 Presigned URL"]


async def update_progress(
    task_id: str,
    status: str,
    progress: float = None,
    payload: ProgressData = ProgressData(),
):
    redis_client.publish(
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
    async with aiohttp.ClientSession() as session:
        yield session


async def async_capture(url: str, capture_id: str):
    async with aiohttp.ClientSession() as session:
        try:
            await update_progress(capture_id, "STARTED")

            # Fetch main HTML
            await update_progress(capture_id, "PROGRESS", 10)
            async with session.get(url) as response:
                html_content = await response.text()

            soup = BeautifulSoup(html_content, "html.parser")

            # Process CSS files
            await update_progress(capture_id, "PROGRESS", 30)
            css_tasks: List[asyncio.Task[str | None]] = []

            for tag in soup.find_all("link", rel="stylesheet"):
                if tag.has_attr("href"):
                    task = asyncio.create_task(
                        fetch_and_store_resource(session, tag["href"], url, capture_id)
                    )
                    css_tasks.append(task)
            css_results = await asyncio.gather(*css_tasks)
            for tag, new_url in zip(
                soup.find_all("link", rel="stylesheet"), css_results
            ):
                if new_url:
                    tag["href"] = new_url

            # Process JavaScript files
            await update_progress(capture_id, "PROGRESS", 50)
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
            await update_progress(capture_id, "PROGRESS", 70)
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
            await update_progress(capture_id, "PROGRESS", 90)
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
                capture_id, "COMPLETE", 100, ProgressData(presigned_url=capture_url)
            )
            return {
                "status": "Website captured successfully",
                "presigned_url": capture_url,
            }

        except Exception as e:
            await update_progress(capture_id, "ERROR")
            print("ERROR: IN CAPTURE WEB SITE: ", str(e))
            print("ERROR: IN CAPTURE WEB SITE: ", e.__traceback__)
            logger.error(f"Task failed for URL: {url}, Task ID: {capture_id}")
            logger.error("Exception details:", exc_info=True)
            return {"status": "Error", "message": str(e)}


@huey.task(context=True)
def capture_website(url: str, task: HueyTask = None):
    if task:
        # This is the task execution path
        capture_id: str = task.id
        return asyncio.run(async_capture(url, capture_id))
    else:
        # This is the task enqueue path
        # We don't have a task ID yet, so we just return
        # The actual execution will happen later
        return
