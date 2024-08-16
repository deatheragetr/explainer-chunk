from typing import Optional, TYPE_CHECKING, Union
import json
from config.redis import Redis
from config.redis_pubsub_channels import (
    PubSubChannel,
    PUBSUB_CONFIG,
    WebCaptureProgressData,
    SummaryProgressData,
)


if TYPE_CHECKING:
    RedisType = Redis[bytes]
else:
    RedisType = Redis


class ProgressUpdater:
    def __init__(
        self,
        redis_client: RedisType,
        document_upload_id: str,
        pub_channel: Union[PubSubChannel, str],
    ):
        self.redis_client = redis_client
        self.document_upload_id = document_upload_id
        if isinstance(pub_channel, str):
            if not PUBSUB_CONFIG.is_valid_channel(pub_channel):
                raise ValueError(f"Invalid pub_channel: {pub_channel}")
            self.pub_channel = PubSubChannel(pub_channel)
        else:
            self.pub_channel = pub_channel

    async def update(
        self,
        progress: float,
        status: str = "PROGRESS",
        payload: Optional[Union[WebCaptureProgressData, SummaryProgressData]] = None,
    ):
        await self.redis_client.publish(
            PUBSUB_CONFIG.get_channel_name(self.pub_channel),
            json.dumps(
                {
                    "connection_id": self.document_upload_id,
                    "status": status,
                    "progress": progress,
                    "payload": payload or {},
                }
            ),
        )

    async def complete(
        self, payload: Union[WebCaptureProgressData, SummaryProgressData]
    ):
        await self.update(100, "COMPLETE", payload)

    async def error(self):
        await self.update(0, "ERROR")
