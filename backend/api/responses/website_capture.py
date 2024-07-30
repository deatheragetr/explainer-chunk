from pydantic import BaseModel
from typing import Annotated


class WebsiteCaptureResponse(BaseModel):
    task_id: Annotated[str, "ID of task"]
