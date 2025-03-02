from pydantic import BaseModel, field_validator
from typing import Annotated


class WebsiteCaptureRequest(BaseModel):
    url: Annotated[str, "URL of website to capture"]
    document_upload_id: Annotated[
        str, "MongoDB ObjectId of document_upload to associate with capture"
    ]
    # TODO: Share mongodb id validation logic with other models

    @field_validator("url")
    def validate_url(cls, v: str) -> str:
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("URL must start with http:// or https://")
        return v
