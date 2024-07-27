from pydantic import BaseModel
from typing import List


class InitiateMultipartUploadRequest(BaseModel):
    file_name: str
    file_type: str

class GetUploadUrlRequest(BaseModel):
    upload_id: str
    file_key: str
    part_number: int

class Part(BaseModel):
    ETag: str
    PartNumber: int

class CompleteMultipartUploadRequest(BaseModel): 
    file_key: str
    parts: List[Part]