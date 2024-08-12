from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id} connected")

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].close()
                logger.info(f"Closed connection for client {client_id}")
            except RuntimeError as e:
                logger.warning(f"Error closing connection for client {client_id}: {str(e)}")
            finally:
                del self.active_connections[client_id]

    async def send_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_text(message)
            except WebSocketDisconnect:
                logger.warning(f"Client {client_id} disconnected while sending message")
                await self.disconnect(client_id)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {str(e)}")
                await self.disconnect(client_id)

    async def broadcast(self, message: str):
        disconnected_clients: list[str] = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                logger.warning(f"Client {client_id} disconnected during broadcast")
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
                disconnected_clients.append(client_id)
 
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def shutdown(self):
        logger.info("Initiating WebSocket manager shutdown")
        await self.broadcast("Server is shutting down. Goodbye!")
        for client_id in list(self.active_connections.keys()):
            await self.disconnect(client_id)
        logger.info("WebSocket manager shutdown complete")


_websocket_manager: Optional[WebSocketManager] = None

def get_websocket_manager() -> WebSocketManager:
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
