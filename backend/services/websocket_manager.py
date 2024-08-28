from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from typing import Optional
from config.logger import get_logger


class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.logger = get_logger()

    def connection_key(self, client_id: str, prefix: str) -> str:
        return f"{prefix}:{client_id}"

    async def connect(self, websocket: WebSocket, client_id: str, prefix: str):
        await websocket.accept()
        key = self.connection_key(client_id, prefix)
        self.active_connections[key] = websocket
        self.logger.info(f"Client {key} connected")

    async def disconnect(self, client_id: str, prefix: str):
        key = self.connection_key(client_id, prefix)
        if key in self.active_connections:
            try:
                await self.active_connections[key].close()
                self.logger.info(f"Closed connection for client {key}")
            except RuntimeError as e:
                self.logger.warning(
                    f"Error closing connection for client {key}: {str(e)}"
                )
            finally:
                del self.active_connections[key]

    async def send_message(self, message: str, client_id: str, prefix: str):
        key = self.connection_key(client_id, prefix)
        if key in self.active_connections:
            try:
                await self.active_connections[key].send_text(message)
            except WebSocketDisconnect:
                self.logger.warning(f"Client {key} disconnected while sending message")
                await self.disconnect(client_id, prefix)
            except Exception as e:
                self.logger.error(f"Error sending message to client {key}: {str(e)}")
                await self.disconnect(client_id, prefix)

    async def broadcast(self, message: str, prefix: Optional[str] = None):
        disconnected_clients: list[tuple[str, str]] = []
        for key, connection in self.active_connections.items():
            if prefix is None or key.startswith(f"{prefix}:"):
                try:
                    await connection.send_text(message)
                except WebSocketDisconnect:
                    self.logger.warning(f"Client {key} disconnected during broadcast")
                    pre, client_id = key.split(":", 1) if ":" in key else ("", key)
                    disconnected_clients.append((pre, client_id))
                except Exception as e:
                    self.logger.error(f"Error broadcasting to client {key}: {str(e)}")
                    pre, client_id = key.split(":", 1) if ":" in key else ("", key)
                    disconnected_clients.append((pre, client_id))

        for prefix, client_id in disconnected_clients:
            await self.disconnect(client_id, prefix)

    async def shutdown(self):
        self.logger.info("Initiating WebSocket manager shutdown")
        await self.broadcast("Server is shutting down. Goodbye!")
        for key in list(self.active_connections.keys()):
            prefix, client_id = key.split(":", 1)
            await self.disconnect(client_id, prefix)
        self.logger.info("WebSocket manager shutdown complete")


_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
