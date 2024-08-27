import asyncio
import json
from typing import Dict, Optional, Any, Coroutine, Protocol, TYPE_CHECKING, Union

from config.redis import Redis
from utils.valid_json import is_valid_json
from services.websocket_manager import WebSocketManager
from config.redis_pubsub_channels import PUBSUB_CONFIG, PubSubChannel

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    RedisType = Redis[str]
else:
    RedisType = Redis


class PubSub(Protocol):
    def subscribe(self, *args: str) -> Coroutine[Any, Any, Any]: ...
    def get_message(
        self, ignore_subscribe_messages: bool = False
    ) -> Coroutine[Any, Any, Optional[Dict[str, Any]]]: ...
    def unsubscribe(self) -> Coroutine[Any, Any, Any]: ...


CHANNEL_TO_SOCKET_PREFIX_MAP: Dict[PubSubChannel, str] = {
    PubSubChannel.CAPTURE_WEBSITE: "document_upload",
    PubSubChannel.SUMMARIZE_DOCUMENT: "summary",
    PubSubChannel.EXLAIN_TEXT: "explain_text",
}


class RedisSubscriber:
    def __init__(self, redis_client: RedisType, websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.is_running = False
        self.task: Optional[asyncio.Task[None]] = None

    async def start(self):
        self.pubsub: PubSub = self.redis_client.pubsub()

        # Subscribe to all channels defined in PUBSUB_CONFIG
        channels_to_subscribe = [channel.value for channel in PubSubChannel]
        await self.pubsub.subscribe(*channels_to_subscribe)

        self.is_running = True
        logger.info(
            f"Redis subscriber started and subscribed to channels: {', '.join(channels_to_subscribe)}"
        )

        while self.is_running:
            try:
                message: Optional[Dict[str, Any]] = await asyncio.wait_for(
                    self.pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0
                )
                if message is not None:
                    await self.process_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Redis subscriber received cancellation signal")
                break
            except Exception as e:
                logger.exception(e)
                logger.error(f"Error in redis subscriber")
                await asyncio.sleep(1)

        await self.cleanup()

    async def process_message(self, message: Dict[str, Any]):
        if is_valid_json(message["data"]):
            data = json.loads(message["data"])
            channel = message.get("channel", "").decode("utf-8")

            if PUBSUB_CONFIG.is_valid_channel(channel):
                socket_prefix = CHANNEL_TO_SOCKET_PREFIX_MAP[PubSubChannel(channel)]

                await self.websocket_manager.send_message(
                    json.dumps(data), data["connection_id"], socket_prefix
                )
            else:
                logger.warning(f"Received message from unknown channel: {channel}")

    async def stop(self):
        logger.info("Stopping Redis subscriber")
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def cleanup(self):
        if self.pubsub:
            await self.pubsub.unsubscribe()
        logger.info("Redis subscriber cleaned up")
