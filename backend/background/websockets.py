from typing import Dict, Optional, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, FastAPI
from redis.asyncio.client import PubSub
import asyncio
import json

websocket_connections: Dict[str, WebSocket] = {}
router = APIRouter()

@router.websocket("/ws/{ws_id}")
async def websocket_endpoint(websocket: WebSocket, ws_id: str):
    await websocket.accept()
    websocket_connections[ws_id] = websocket
    print("Websocket connections (from controller): ", websocket_connections)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        del websocket_connections[ws_id]

# Redis subscriber
async def redis_subscriber(app: FastAPI):
    redis_client = await app.state.redis_pool.get_client()
    pubsub: PubSub = redis_client.pubsub()
    await pubsub.subscribe("capture_website_task")

    while True:
        try:
            message: Optional[Dict[str, Any]] = await pubsub.get_message(
                ignore_subscribe_messages=True
            )
            if message is not None:
                print(f"Got message: {message}")
                if message["data"] is not None:
                    print(f"Type of message Data: {type(message['data'])}")
                    data = json.loads(message["data"])
                    print(f"Type of Client Id: {type(data['connection_id'])}")
                    print("Websocket connections (from redis subscriber): ", websocket_connections)
                    if data["connection_id"] in websocket_connections:
                        await websocket_connections[data["connection_id"]].send_text(
                            json.dumps(data)
                        )
        except Exception as e:
            print(f"Error in redis subscriber: {e}")
            await asyncio.sleep(1)  # Wait a bit before retrying