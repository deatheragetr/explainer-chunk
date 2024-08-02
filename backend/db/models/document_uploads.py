from typing import TypedDict, Annotated, Literal, Optional, Union
from api.utils.url_friendly import make_url_friendly
from bson import ObjectId
from enum import Enum
from config.environment import WasabiSettings

settings = WasabiSettings()


class AllowedS3Buckets(str, Enum):
    DOCUMENT_UPLOADS = settings.wasabi_document_bucket
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


class MongoDocumentUpload(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    file_details: Annotated[MongoFileDetails, "Details of the uploaded file"]


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


# Example usage:
# web_file = create_mongo_file_details(
#     file_name="example.pdf",
#     file_type="pdf",
#     file_key="documents/example.pdf",
#     url_friendly_file_name="example-pdf",
#     s3_bucket="my-bucket",
#     s3_url="https://my-bucket.s3.amazonaws.com/documents/example.pdf",
#     source=SourceType.WEB,
#     source_url="https://example.com/original-file.pdf"
# )
#
# upload_file = create_mongo_file_details(
#     file_name="upload.docx",
#     file_type="docx",
#     file_key="documents/upload.docx",
#     url_friendly_file_name="upload-docx",
#     s3_bucket="my-bucket",
#     s3_url="https://my-bucket.s3.amazonaws.com/documents/upload.docx",
#     source=SourceType.FILE_UPLOAD
# )
