from pydantic import BaseModel, field_validator
from typing import Annotated
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
