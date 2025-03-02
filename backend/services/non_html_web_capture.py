from typing import Dict, cast
from logging import Logger
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


def get_file_extension_from_content_type(content_type: str) -> str:
    """Get file extension based on content type."""
    content_type = content_type.split(";")[0].strip().lower()

    extension_map = {
        "application/pdf": ".pdf",
        "application/msword": ".doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/vnd.ms-powerpoint": ".ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
        "text/plain": ".txt",
        "text/csv": ".csv",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "application/json": ".json",
        "application/xml": ".xml",
        "text/xml": ".xml",
    }

    return extension_map.get(content_type, ".bin")


async def capture_non_html(
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
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        file_extension = get_file_extension_from_content_type(content_type)
        file_name = f"download{file_extension}"

        # Download the file content
        await progress_updater.update(50)
        file_content = await response.read()

        # Store the file in S3
        await progress_updater.update(70)
        s3_key = generate_s3_key_for_file(
            folder=AllowedFolders.WEB_CAPTURES,
            object_id=ObjectId(document_upload_id),
            file_name=file_name,
        )
        s3_client.put_object(
            Bucket=AllowedS3Buckets.PUBLIC_BUCKET.value,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
        )

        s3_settings = S3Settings()
        s3_url = generate_s3_url(
            s3_settings.s3_host, AllowedS3Buckets.PUBLIC_BUCKET, s3_key
        )
        mongo_file_details = create_mongo_file_details(
            file_name=file_name,
            file_type=content_type,
            file_key=s3_key,
            s3_url=s3_url,
            s3_bucket=AllowedS3Buckets.PUBLIC_BUCKET.value,
            source=SourceType.WEB,
            source_url=url,
        )

        # Extract text and metadata
        await progress_updater.update(80)
        extracted_text, extracted_metadata = await extract_text_and_metadata(
            file_content, content_type
        )

        # Create document in MongoDB
        await progress_updater.update(90)
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
            payload=WebCaptureProgressData(
                presigned_url=s3_url,
                file_type=content_type,
                file_name=file_name,
                document_upload_id=document_upload_id,
                url_friendly_file_name=mongo_file_details["url_friendly_file_name"],
            )
        )

        return {
            "status": "File downloaded and stored successfully",
            "presigned_url": s3_url,
        }

    except Exception as e:
        await progress_updater.error()
        logger.error(
            f"Direct download failed for URL: {url}, Task ID: {document_upload_id}"
        )
        logger.exception("Exception details: ", e)
        raise
