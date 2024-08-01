from pydantic import BaseModel, Field, field_validator
import re
from typing import Annotated


class DocumentUploadResponse(BaseModel):
    id: Annotated[str, "Primary identifier of the document (Mongo Primary Key)"]
    file_name: Annotated[str, "Original File Name"]
    file_type: Annotated[str, "MIME type of file, e.g, application/pdf"]
    url_friendly_file_name: Annotated[
        str, "URL friendly version of file_name (no spaces, non-ASCII chars, etc.)"
    ]


class DocumentRetrieveResponse(DocumentUploadResponse):
    presigned_url: Annotated[str, "pre-signed URL to file in S3"]


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
