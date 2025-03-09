from pydantic import BaseModel, field_validator
from typing import Annotated, Dict, Any, Optional
import re
from bson import ObjectId


def validate_file_key(v: str) -> str:
    pattern = r"^document_uploads/([0-9a-fA-F]{24})-(.+)$"
    if not re.match(pattern, v):
        raise ValueError("Invalid file_key format")
    return v


FileKeyField = Annotated[str, validate_file_key]


class DocumentUploadRequest(BaseModel):
    file_name: Annotated[str, "Name of file"]
    file_type: Annotated[str, "MIME type of file, e.g, application/pdf"]
    file_key: FileKeyField
    extracted_text: Annotated[str, "Extracted text from the document"]
    extracted_metadata: Annotated[
        Dict[str, Any], "Extracted metadata from the document"
    ]

    # Redundant?
    @field_validator("file_key")
    def extract_object_id(cls, v: str) -> str:
        match = re.match(r"^document_uploads/([0-9a-fA-F]{24})-", v)
        if not match:
            raise ValueError("Could not extract ObjectId from file_key")
        return v

    @property
    def extracted_object_id(self) -> ObjectId:
        match = re.match(r"^document_uploads/([0-9a-fA-F]{24})-", self.file_key)
        if match:
            return ObjectId(match.group(1))
        raise ValueError("Could not extract ObjectId from file_key")


class NoteRequest(BaseModel):
    content: Annotated[str, "Content of the note"]


class CustomTitleRequest(BaseModel):
    title: Annotated[str, "Custom title for the document"]


class DocumentUpdateRequest(BaseModel):
    """Request model for updating document properties"""

    custom_title: Optional[str] = None

    class Config:
        json_schema_extra = {"example": {"custom_title": "My Custom Document Title"}}
