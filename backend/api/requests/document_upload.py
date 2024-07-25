from pydantic import BaseModel
from typing import Annotated

class DocumentUploadRequest(BaseModel):
    file_name: Annotated[str, 'Name of file']
    file_type: Annotated[str, 'MIME type of file, e.g, application/pdf']
    file_key: Annotated[str, 'File key in Wasabi/S3']

