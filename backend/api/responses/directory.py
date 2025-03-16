from typing import List, Optional
from pydantic import BaseModel, Field


class DirectoryResponse(BaseModel):
    """Response model for a directory"""

    id: str = Field(..., description="Directory ID")
    user_id: str = Field(..., description="User ID")
    name: str = Field(..., description="Directory name")
    parent_id: Optional[str] = Field(None, description="Parent directory ID")
    path: str = Field(..., description="Full path of the directory")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class LightweightDocumentResponse(BaseModel):
    """Minimal document representation for directory listings"""

    id: str = Field(..., description="Document ID")
    file_name: str = Field(..., description="Original file name")
    file_type: str = Field(..., description="MIME type of file")
    url_friendly_file_name: str = Field(..., description="URL friendly file name")
    title: str = Field(..., description="Display title")


class DirectoryContentsResponse(BaseModel):
    """Response model for directory contents"""

    directories: List[DirectoryResponse] = Field(
        [], description="List of subdirectories"
    )
    documents: List[LightweightDocumentResponse] = Field(
        [], description="List of documents in the directory"
    )


class DirectoryListResponse(BaseModel):
    """Response model for a list of directories"""

    directories: List[DirectoryResponse] = Field([], description="List of directories")
