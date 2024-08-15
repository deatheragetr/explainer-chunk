from typing import TypedDict, Optional, Annotated, TYPE_CHECKING
import json
from config.redis import Redis


class ProgressData(TypedDict, total=False):
    presigned_url: Annotated[Optional[str], "S3 Presigned URL"]
    file_type: Annotated[Optional[str], "File Type"]
    file_name: Annotated[Optional[str], "File Name"]
    document_upload_id: Annotated[Optional[str], "Document Upload ID"]
    url_friendly_file_name: Annotated[
        Optional[str], "URL-friendly version of the file name"
    ]


if TYPE_CHECKING:
    RedisType = Redis[bytes]
else:
    RedisType = Redis


class ProgressUpdater:
    def __init__(self, redis_client: RedisType, document_upload_id: str):
        self.redis_client = redis_client
        self.document_upload_id = document_upload_id

    async def update(
        self,
        progress: float,
        status: str = "PROGRESS",
        payload: Optional[ProgressData] = None,
    ):
        await self.redis_client.publish(
            "capture_website_task",
            json.dumps(
                {
                    "connection_id": self.document_upload_id,
                    "status": status,
                    "progress": progress,
                    "payload": payload or {},
                }
            ),
        )

    async def complete(self, payload: ProgressData):
        await self.update(100, "COMPLETE", payload)

    async def error(self):
        await self.update(0, "ERROR")
