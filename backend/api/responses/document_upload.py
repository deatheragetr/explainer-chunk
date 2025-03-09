from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
import re
from typing import Annotated


class ThumbnailInfo(BaseModel):
    presigned_url: str


class NoteResponse(BaseModel):
    content: Annotated[str, "Content of the note"]


class DocumentUploadResponse(BaseModel):
    id: Annotated[str, "Primary identifier of the document (Mongo Primary Key)"]
    file_name: Annotated[str, "Original File Name"]
    file_type: Annotated[str, "MIME type of file, e.g, application/pdf"]
    url_friendly_file_name: Annotated[
        str, "URL friendly version of file_name (no spaces, non-ASCII chars, etc.)"
    ]
    note: Annotated[Optional[NoteResponse], "End User notes on the document"]
    custom_title: Annotated[Optional[str], "User-defined custom title for the document"]
    title: Annotated[str, "Display title based on precedence rules"]
    directory_id: Annotated[
        Optional[str], "ID of the directory this document belongs to"
    ]
    directory_path: Annotated[
        Optional[str], "Path of the directory this document belongs to"
    ]


class DocumentRetrieveResponseForPage(DocumentUploadResponse):
    thumbnail: Annotated[Optional[ThumbnailInfo], "Thumbnail information"]
    extracted_metadata: Annotated[
        Optional[Dict[str, Any]], "Metadata extracted from file/import"
    ]


class DocumentRetrieveResponse(DocumentUploadResponse):
    presigned_url: Annotated[str, "pre-signed URL to document file in S3"]


class DocumentUploadImportExternalResponse(BaseModel):
    id: Annotated[
        str,
        Field(..., description="Primary identifier of the document (MongoDB ObjectId)"),
    ]

    @field_validator("id")
    def validate_object_id(cls, v: str) -> str:
        if not re.match(r"^[0-9a-fA-F]{24}$", v):
            raise ValueError("Invalid MongoDB ObjectId format")
        return v

    class Config:
        json_schema_extra = {"example": {"id": "507f1f77bcf86cd799439011"}}


class PaginatedDocumentUploadsResponse(BaseModel):
    documents: List[DocumentRetrieveResponseForPage]
    next_cursor: Optional[str] = None
