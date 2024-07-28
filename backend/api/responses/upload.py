from pydantic import BaseModel

class InitiateMultipartUploadResponse(BaseModel):
    upload_id: str
    file_key: str


class GetUploadUrlResponse(BaseModel):
    presigned_url: str