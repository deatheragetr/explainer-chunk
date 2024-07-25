from pydantic import BaseModel

class UploadFileInfoRequest(BaseModel):
    filename: str
    file_type: str