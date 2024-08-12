# redis_subscriber.py
from typing import Dict, Optional, Any, cast, Protocol, Coroutine
from fastapi import FastAPI
import asyncio
import json
from config.redis import RedisType
from utils.valid_json import is_valid_json
# from redis.asyncio.client import PubSub
from services.websocket_manager import WebSocketManager

class PubSub(Protocol):
    def subscribe(self, *args: str) -> Coroutine[Any, Any, Any]: ...
    def get_message(self, ignore_subscribe_messages: bool = False) -> Coroutine[Any, Any, Optional[Dict[str, Any]]]: ...


async def redis_subscriber(app: FastAPI):
    redis_client: RedisType = await app.state.redis_pool.get_client()
    websocket_manager: WebSocketManager = app.state.websocket_manager
    # pubsub: PubSub  = redis_client.pubsub()
    pubsub = cast(PubSub, redis_client.pubsub())

    await pubsub.subscribe("capture_website_task")

    while True:
        try:
            message: Optional[Dict[str, Any]] = await pubsub.get_message(
                ignore_subscribe_messages=True
            )
            if message is not None:
                if (is_valid_json(message["data"])):
                    data = json.loads(message["data"])
                    print(f"Type of Client Id: {type(data['connection_id'])}")
                    await websocket_manager.send_message(
                        json.dumps(data), data["connection_id"]
                    )
        except Exception as e:
            print(f"Error in redis subscriber: {e}")
            await asyncio.sleep(1)  # Wait a bit before retrying