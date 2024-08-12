# websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from services.websocket_manager import WebSocketManager

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, websocket_manager: WebSocketManager = Depends()):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text()
            # data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            # For example, you might want to broadcast this message
            # await websocket_manager.broadcast(data)
    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)