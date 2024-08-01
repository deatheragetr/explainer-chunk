from pydantic import BaseModel
from typing import Annotated


class WebsiteCaptureResponse(BaseModel):
    url: Annotated[str, "url"]
    document_upload_id: Annotated[str, "document_upload_id"]
