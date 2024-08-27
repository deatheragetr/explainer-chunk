from enum import Enum
from typing import Dict, Any, TypedDict, Optional, Annotated


class PubSubChannel(Enum):
    CAPTURE_WEBSITE = "capture_website_task"
    SUMMARIZE_DOCUMENT = "summarize_document_task"
    EXLAIN_TEXT = "explain_text_task"


class WebCaptureProgressData(TypedDict, total=False):
    presigned_url: Annotated[Optional[str], "S3 Presigned URL"]
    file_type: Annotated[Optional[str], "File Type"]
    file_name: Annotated[Optional[str], "File Name"]
    document_upload_id: Annotated[Optional[str], "Document Upload ID"]
    url_friendly_file_name: Annotated[
        Optional[str], "URL-friendly version of the file name"
    ]


class SummaryProgressData(TypedDict, total=False):
    newText: Annotated[Optional[str], "New text to append to the summary"]
    completeText: Annotated[Optional[str], "Full text of the summary"]


class ExplainTextProgressData(TypedDict, total=False):
    newText: Annotated[Optional[str], "New text to append to the summary"]
    completeText: Annotated[Optional[str], "Full text of the summary"]


class PubSubConfig:
    def __init__(self):
        self.channels: Dict[PubSubChannel, Dict[str, Any]] = {
            PubSubChannel.CAPTURE_WEBSITE: {"payload_type": WebCaptureProgressData},
            PubSubChannel.SUMMARIZE_DOCUMENT: {"payload_type": SummaryProgressData},
            PubSubChannel.EXLAIN_TEXT: {"payload_type": ExplainTextProgressData},
        }

    def get_channel_name(self, channel: PubSubChannel) -> str:
        return channel.value

    def get_channel_config(self, channel: PubSubChannel) -> Dict[str, Any]:
        return self.channels[channel]

    def is_valid_channel(self, channel_name: str) -> bool:
        return any(channel.value == channel_name for channel in PubSubChannel)

    @property
    def all_payload_types(self):
        return tuple(config["payload_type"] for config in self.channels.values())


PUBSUB_CONFIG = PubSubConfig()
