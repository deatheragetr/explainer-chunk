from pydantic import BaseModel
from typing import Annotated

class DocumentUploadResponse(BaseModel):
    id: Annotated[str, 'Primary identifier of the document (Mongo Primary Key)']
    file_name: Annotated[str, 'Original File Name']
    file_type: Annotated[str, 'MIME type of file, e.g, application/pdf']
    url_friendly_file_name: Annotated[str, 'URL friendly version of file_name (no spaces, non-ASCII chars, etc.)']