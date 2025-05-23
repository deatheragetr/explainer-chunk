from urllib.parse import urlparse
from typing import Dict, Optional
from logging import Logger
import os
from bson import ObjectId
from aiohttp import ClientSession, ClientResponse

from config.mongo import AsyncIOMotorCollection
from config.s3 import s3_client
from config.environment import S3Settings
from db.models.document_uploads import (
    MongoDocumentUpload,
    create_mongo_file_details,
    generate_s3_key_for_file,
    generate_s3_url,
    AllowedFolders,
    AllowedS3Buckets,
    SourceType,
)
from utils.progress_updater import ProgressUpdater, WebCaptureProgressData
from utils.text_and_metadata_extractor import extract_text_and_metadata
from services.openai_assistant_service import OpenAIAssistantService

from config.environment import OpenAISettings

openai_settings = OpenAISettings()

from config.ai_models import DEFAULT_MODEL_CONFIGS


async def capture_non_html(
    progress_updater: ProgressUpdater,
    session: ClientSession,
    mongo_collection: AsyncIOMotorCollection[MongoDocumentUpload],
    url: str,
    response: ClientResponse,
    document_upload_id: str,
    normalized_file_type: str,
    logger: Logger,
    user_id: str,
    directory_id: Optional[str] = None,
) -> Dict[str, str]:
    try:
        await progress_updater.update(50)
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
            Bucket=AllowedS3Buckets.DOCUMENT_UPLOADS.value,
            Key=s3_key,
            Body=content,
            ContentType=content_type,
        )

        await progress_updater.update(75)

        capture_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AllowedS3Buckets.DOCUMENT_UPLOADS.value, "Key": s3_key},
            ExpiresIn=3600,
        )

        s3_settings = S3Settings()
        s3_url = generate_s3_url(
            s3_settings.s3_host, AllowedS3Buckets.DOCUMENT_UPLOADS, s3_key
        )

        await progress_updater.update(85)
        mongo_file_details = create_mongo_file_details(
            file_name=file_name,
            file_type=normalized_file_type,
            file_key=s3_key,
            s3_url=s3_url,
            s3_bucket=AllowedS3Buckets.DOCUMENT_UPLOADS.value,
            source=SourceType.WEB,
            source_url=url,
        )

        extracted_text, extracted_metadata = await extract_text_and_metadata(
            content, normalized_file_type
        )

        document: MongoDocumentUpload = {
            "_id": ObjectId(document_upload_id),
            "user_id": ObjectId(user_id),
            "file_details": mongo_file_details,
            "extracted_metadata": extracted_metadata,
            "extracted_text": extracted_text,
            "openai_assistants": [],
            "chats": [],
            "custom_title": None,
            "thumbnail": None,
            "note": None,
            "directory_id": ObjectId(directory_id) if directory_id else None,
            "directory_path": None,  # Will be populated if directory_id is provided
        }

        # If directory_id is provided, fetch the directory path
        if directory_id:
            directory = await mongo_collection.database.directories.find_one(
                {"_id": ObjectId(directory_id), "user_id": ObjectId(user_id)}
            )
            if directory:
                document["directory_path"] = directory.get("path")

        # TODO: Grab default model config for user
        openai_assistant_service = OpenAIAssistantService(
            openai_api_key=openai_settings.openai_api_key
        )
        assistant_details = await openai_assistant_service.create_assistant_thread(
            model_config=DEFAULT_MODEL_CONFIGS["gpt-4o-mini"],
            document=document,
            mongo_collection=mongo_collection,
        )
        document["openai_assistants"].append(assistant_details)

        await mongo_collection.update_one(
            {"_id": ObjectId(document_upload_id)},
            {"$set": document},
            upsert=True,
        )

        await progress_updater.complete(
            payload=WebCaptureProgressData(
                presigned_url=capture_url,
                file_type=normalized_file_type,
                file_name=file_name,
                document_upload_id=document_upload_id,
                url_friendly_file_name=document["file_details"][
                    "url_friendly_file_name"
                ],
            )
        )

        return {
            "status": "File downloaded and stored successfully",
            "presigned_url": capture_url,
        }

    except Exception as e:
        await progress_updater.error()
        logger.error(
            f"Direct download failed for URL: {url}, Task ID: {document_upload_id}"
        )
        logger.exception("Exception details: ", e)
        raise
