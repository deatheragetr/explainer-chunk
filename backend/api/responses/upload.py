from pydantic import BaseModel

class UploadFileInfoResponse(BaseModel):
    presigned_url: str
    file_key: str