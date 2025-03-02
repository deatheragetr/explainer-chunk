import asyncio
from typing import List, Dict, Optional, Any, cast
from bs4 import BeautifulSoup
from bson import ObjectId
from aiohttp import ClientSession, ClientResponse
from logging import Logger

from config.s3 import s3_client
from config.environment import S3Settings
from config.mongo import AsyncIOMotorCollection
from db.models.document_uploads import (
    MongoDocumentUpload,
    create_mongo_file_details,
    generate_s3_key_for_web_capture,
    generate_s3_url,
    AllowedFolders,
    AllowedS3Buckets,
    SourceType,
)
from utils.progress_updater import ProgressUpdater, WebCaptureProgressData
from utils.fetch_and_store import fetch_and_store_resource
from utils.text_and_metadata_extractor import extract_text_and_metadata
from services.openai_assistant_service import OpenAIAssistantService
from config.environment import OpenAISettings

openai_settings = OpenAISettings()

from config.ai_models import DEFAULT_MODEL_CONFIGS

s3_settings = S3Settings()
S3_HOST = s3_settings.s3_host


async def capture_html(
    progress_updater: ProgressUpdater,
    session: ClientSession,
    mongo_collection: AsyncIOMotorCollection[MongoDocumentUpload],
    url: str,
    response: ClientResponse,
    document_upload_id: str,
    user_id: str,
    logger: Logger,
) -> Dict[str, str]:
    try:
        html_content = await response.text()
        soup = BeautifulSoup(html_content, "html.parser")

        # Process CSS files
        await progress_updater.update(30)
        css_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("link", rel="stylesheet"):
            if tag.has_attr("href"):
                task: asyncio.Task[Any] = asyncio.create_task(
                    fetch_and_store_resource(
                        session,
                        tag["href"],
                        url,
                        document_upload_id,
                        AllowedS3Buckets.PUBLIC_BUCKET,
                        s3_client,
                        S3_HOST,
                        logger,
                    )
                )
                css_tasks.append(task)
        css_results = await asyncio.gather(*css_tasks)
        for tag, new_url in zip(soup.find_all("link", rel="stylesheet"), css_results):
            if new_url:
                tag["href"] = new_url

        # Process JavaScript files
        await progress_updater.update(50)
        js_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("script", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(
                    session,
                    tag["src"],
                    url,
                    document_upload_id,
                    AllowedS3Buckets.PUBLIC_BUCKET,
                    s3_client,
                    S3_HOST,
                    logger,
                )
            )
            js_tasks.append(task)
        js_results = await asyncio.gather(*js_tasks)
        for tag, new_url in zip(soup.find_all("script", src=True), js_results):
            if new_url:
                tag["src"] = new_url

        # Process images
        await progress_updater.update(70)
        img_tasks: List[asyncio.Task[Optional[str]]] = []
        for tag in soup.find_all("img", src=True):
            task = asyncio.create_task(
                fetch_and_store_resource(
                    session,
                    tag["src"],
                    url,
                    document_upload_id,
                    AllowedS3Buckets.PUBLIC_BUCKET,
                    s3_client,
                    S3_HOST,
                    logger,
                )
            )
            img_tasks.append(task)
        img_results = await asyncio.gather(*img_tasks)
        for tag, new_url in zip(soup.find_all("img", src=True), img_results):
            if new_url:
                tag["src"] = new_url

        # Store the modified HTML
        await progress_updater.update(90)
        html_key = generate_s3_key_for_web_capture(
            folder=AllowedFolders.WEB_CAPTURES,
            object_id=ObjectId(document_upload_id),
            file_name="index.html",
        )
        s3_client.put_object(
            Bucket=AllowedS3Buckets.PUBLIC_BUCKET.value,
            Key=html_key,
            Body=str(soup),
            ContentType="text/html",
        )

        s3_settings = S3Settings()
        s3_url = generate_s3_url(
            s3_settings.s3_host, AllowedS3Buckets.PUBLIC_BUCKET, html_key
        )
        mongo_file_details = create_mongo_file_details(
            file_name="index.html",
            file_type="text/html",
            file_key=html_key,
            s3_url=s3_url,
            s3_bucket=AllowedS3Buckets.PUBLIC_BUCKET.value,
            source=SourceType.WEB,
            source_url=url,
        )

        modified_html_content = str(soup)

        extracted_text, extracted_metadata = await extract_text_and_metadata(
            modified_html_content.encode("utf-8"), "text/html"
        )

        # Create document in MongoDB
        document_data = {
            "_id": ObjectId(document_upload_id),
            "user_id": ObjectId(user_id),
            "file_details": mongo_file_details,
            "extracted_text": extracted_text,
            "extracted_metadata": extracted_metadata,
            "openai_assistants": [],
            "chats": [],
            "thumbnail": None,
            "note": None,
        }

        # TODO: Grab default model config for user
        openai_assistant_service = OpenAIAssistantService(
            openai_api_key=openai_settings.openai_api_key
        )
        assistant_details = await openai_assistant_service.create_assistant_thread(
            model_config=DEFAULT_MODEL_CONFIGS["gpt-4o-mini"],
            document=cast(MongoDocumentUpload, document_data),
            mongo_collection=mongo_collection,
        )

        # Add the assistant details to the document
        document_data["openai_assistants"] = [assistant_details]

        await mongo_collection.update_one(
            {"_id": ObjectId(document_upload_id)},
            {"$set": document_data},
            upsert=True,
        )

        await progress_updater.complete(
            WebCaptureProgressData(
                presigned_url=s3_url,
                file_type="text/html",
                file_name="index.html",
                document_upload_id=document_upload_id,
                url_friendly_file_name=mongo_file_details["url_friendly_file_name"],
            )
        )

        return {
            "status": "Website captured successfully",
            "presigned_url": s3_url,
        }

    except Exception as e:
        await progress_updater.error()
        logger.error(f"Task failed for URL: {url}, Task ID: {document_upload_id}")
        logger.exception("Exception details: ", e)
        raise
