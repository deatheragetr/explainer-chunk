from typing import (
    TypedDict,
    Annotated,
    Literal,
    Optional,
    Union,
    Dict,
    Any,
    List,
    cast,
    Mapping,
)
from api.utils.url_friendly import make_url_friendly
from bson import ObjectId
from enum import Enum
from config.environment import S3Settings
from config.ai_models import ModelName


settings = S3Settings()


class AllowedS3Buckets(str, Enum):
    DOCUMENT_UPLOADS = settings.s3_document_bucket
    PUBLIC_BUCKET = settings.s3_public_bucket


class AllowedFolders(str, Enum):
    WEB_CAPTURES = "web_captures"
    DOCUMENT_UPLOADS = "document_uploads"


S3Bucket = Literal[AllowedS3Buckets.DOCUMENT_UPLOADS, AllowedS3Buckets.PUBLIC_BUCKET]
Folder = Literal[AllowedFolders.WEB_CAPTURES, AllowedFolders.DOCUMENT_UPLOADS]


class SourceType(str, Enum):
    WEB = "web"
    FILE_UPLOAD = "file_upload"


class MongoFileDetailsBase(TypedDict):
    file_name: Annotated[str, "Name of the file"]
    file_type: Annotated[str, "Type of the file (e.g., pdf, docx)"]
    file_key: Annotated[str, "S3 key for the file"]
    url_friendly_file_name: Annotated[str, "URL-friendly version of the file name"]
    s3_bucket: Annotated[str, "Name of the S3 bucket"]
    s3_url: Annotated[str, "Full S3 URL of the file"]


class MongoFileDetailsWeb(MongoFileDetailsBase):
    source: Literal[SourceType.WEB]
    source_url: Annotated[str, "Original URL of the file if source is web"]


class MongoFileDetailsUpload(MongoFileDetailsBase):
    source: Literal[SourceType.FILE_UPLOAD]


MongoFileDetails = Union[MongoFileDetailsWeb, MongoFileDetailsUpload]


class OpenAIAssistantDetails(TypedDict):
    assistant_id: Annotated[str, "OpenAI Assistant ID"]
    thread_id: Annotated[str, "OpenAI Thread ID"]
    model: Annotated[ModelName, "Model used for this assistant"]
    external_document_upload_id: Optional[
        Annotated[
            str, "ID of the associated document upload, e.g., the file ID from OpenAI"
        ]
    ]
    last_message_id: Optional[Annotated[str, "ID of the last message in the thread"]]


class ChatReference(TypedDict):
    chat_id: Annotated[ObjectId, "Reference to the chat document"]
    model_name: Annotated[ModelName, "Name of the model used for this chat"]


class ThumbnailDetails(TypedDict):
    file_key: Annotated[str, "S3 key for the thumbnail"]
    s3_bucket: Annotated[str, "S3 bucket for the thumbnail"]
    s3_url: Annotated[str, "Full S3 URL of the thumbnail"]


class Note(TypedDict):
    content: Annotated[str, "Content of the note"]


class MongoDocumentUpload(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    user_id: Annotated[ObjectId, "ID of the user who owns this document"]
    file_details: Annotated[MongoFileDetails, "Details of the uploaded file"]
    extracted_text: Annotated[str, "Extracted text content from the document"]
    extracted_metadata: Optional[
        Annotated[
            Dict[str, Any], "Extracted metadata (e.g., author, title) from the document"
        ]
    ]
    custom_title: Optional[Annotated[str, "User-defined custom title for the document"]]
    openai_assistants: Annotated[
        List[OpenAIAssistantDetails], "List of associated OpenAI Assistants"
    ]
    chats: Annotated[List[ChatReference], "List of references to associated chats"]
    thumbnail: Optional[
        Annotated[ThumbnailDetails, "Details of the document thumbnail"]
    ]
    note: Optional[Annotated[Note, "End User notes on the document"]]


def generate_s3_key_for_file(
    folder: Folder, object_id: ObjectId, file_name: str
) -> str:
    url_friendly_file_name = make_url_friendly(file_name)
    return f"{folder.value}/{object_id}-{url_friendly_file_name}"


def generate_s3_key_for_web_capture(
    object_id: ObjectId, file_name: str, folder: Folder
) -> str:
    url_friendly_file_name = make_url_friendly(file_name)
    return f"{folder.value}/{object_id}/{url_friendly_file_name}"


def generate_s3_url(s3_host: str, s3_bucket: S3Bucket, file_key: str) -> str:
    return f"https://{s3_bucket.value}.{s3_host}/{file_key}"


def create_mongo_file_details(
    file_name: str,
    file_type: str,
    s3_bucket: str,
    source: SourceType,
    file_key: str,
    s3_url: str,
    source_url: Optional[str] = None,
) -> MongoFileDetails:
    base_details = {
        "file_name": file_name,
        "file_type": file_type,
        "file_key": file_key,
        "url_friendly_file_name": make_url_friendly(file_name),
        "file_key": file_key,
        "s3_bucket": s3_bucket,
        "s3_url": s3_url,
    }

    if source == SourceType.WEB:
        if source_url is None:
            raise ValueError("source_url is required when source is web")
        return MongoFileDetailsWeb(**base_details, source=source, source_url=source_url)
    else:
        return MongoFileDetailsUpload(**base_details, source=source)


def find_assistant_by_model(document: MongoDocumentUpload, target_model: ModelName):
    assistants = document.get("openai_assistants", [])
    for assistant in assistants:
        if assistant.get("model") == target_model:
            return assistant
    return None


def get_display_title(document: Mapping[str, Any]) -> str:
    """
    Determine the display title for a document based on precedence rules:
    1. Custom title if exists
    2. Extracted metadata title if exists
    3. Extracted metadata /Title (capital slash T) if exists
    4. Fallback to file name
    """
    # 1. Custom title if exists
    if document.get("custom_title"):
        return cast(str, document.get("custom_title"))

    # 2. Extracted metadata title if exists
    if document.get("extracted_metadata") and document.get(
        "extracted_metadata", {}
    ).get("title"):
        return cast(str, document.get("extracted_metadata", {}).get("title"))

    # 3. Extracted metadata Title (capital T) if exists
    if document.get("extracted_metadata") and document.get(
        "extracted_metadata", {}
    ).get("/Title"):
        return cast(str, document.get("extracted_metadata", {}).get("/Title"))

    # 4. Fallback to file name
    return document["file_details"]["file_name"]
