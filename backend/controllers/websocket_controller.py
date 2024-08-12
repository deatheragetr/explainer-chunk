# websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from services.websocket_manager import get_websocket_manager, WebSocketManager

router = APIRouter()

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, websocket_manager: WebSocketManager = Depends(get_websocket_manager)):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            # data = await websocket.receive_text()
            await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        # logger.info(f"Client {client_id} disconnected")
        print(f"Client {client_id} disconnected")
    finally:
        await websocket_manager.disconnect(client_id)
