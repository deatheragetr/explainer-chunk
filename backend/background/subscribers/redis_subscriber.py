import asyncio
import json
from typing import Dict, Optional, Any, Protocol, Coroutine
from config.redis import RedisType
from utils.valid_json import is_valid_json
from services.websocket_manager import WebSocketManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubSub(Protocol):
    def subscribe(self, *args: str) -> Coroutine[Any, Any, Any]: ...
    def get_message(self, ignore_subscribe_messages: bool = False) -> Coroutine[Any, Any, Optional[Dict[str, Any]]]: ...
    def unsubscribe(self) -> Coroutine[Any, Any, Any]: ...

class RedisSubscriber:
    def __init__(self, redis_client: RedisType, websocket_manager: WebSocketManager):
        self.redis_client = redis_client
        self.websocket_manager = websocket_manager
        self.pubsub: Optional[PubSub] = None
        self.is_running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe("capture_website_task")
        self.is_running = True
        logger.info("Redis subscriber started")

        while self.is_running:
            try:
                message: Optional[Dict[str, Any]] = await asyncio.wait_for(
                    self.pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0
                )
                if message is not None:
                    await self.process_message(message)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                logger.info("Redis subscriber received cancellation signal")
                break
            except Exception as e:
                logger.error(f"Error in redis subscriber: {e}")
                await asyncio.sleep(1)

        await self.cleanup()

    async def process_message(self, message: Dict[str, Any]):
        if is_valid_json(message["data"]):
            data = json.loads(message["data"])
            await self.websocket_manager.send_message(
                json.dumps(data), data["connection_id"]
            )

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
