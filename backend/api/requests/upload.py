from pydantic import BaseModel
from typing import List
from mypy_boto3_s3.type_defs import CompletedPartTypeDef


class InitiateMultipartUploadRequest(BaseModel):
    file_name: str
    file_type: str


class GetUploadUrlRequest(BaseModel):
    upload_id: str
    file_key: str
    part_number: int


class CompleteMultipartUploadRequest(BaseModel):
    file_key: str
    parts: List[CompletedPartTypeDef]  # { ETage: str, PartNumber: int }
