# websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from services.websocket_manager import get_websocket_manager, WebSocketManager
from config.logger import get_logger, logging

router = APIRouter()


@router.websocket("/ws/document-upload/{document_upload_id}")
async def document_upload_websocket_endpoint(
    websocket: WebSocket,
    document_upload_id: str,
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
    logger: logging.Logger = Depends(get_logger),
):
    await websocket_manager.connect(websocket, document_upload_id, "document_upload")
    try:
        while True:
            # data = await websocket.receive_text()
            await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        logger.info(
            f"/ws/document-upload/{document_upload_id}  --  Connection for document_upload={document_upload_id} disconnected"
        )
    finally:
        await websocket_manager.disconnect(document_upload_id, "document_upload")


@router.websocket("/ws/document-upload/{document_upload_id}/summary")
async def summarize_websocket_endpoint(
    websocket: WebSocket,
    document_upload_id: str,
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
    logger: logging.Logger = Depends(get_logger),
):
    await websocket_manager.connect(websocket, document_upload_id, "summary")
    try:
        while True:
            # data = await websocket.receive_text()
            await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        logger.info(
            f"/ws/document-upload/{document_upload_id}/summary  --  Connection for summary of document_upload={document_upload_id} disconnected"
        )
    finally:
        await websocket_manager.disconnect(document_upload_id, "summary")


@router.websocket("/ws/document-upload/{document_upload_id}/text-explanation")
async def text_explanation_websocket_endpoint(
    websocket: WebSocket,
    document_upload_id: str,
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
    logger: logging.Logger = Depends(get_logger),
):
    await websocket_manager.connect(websocket, document_upload_id, "explain_text")
    try:
        while True:
            # data = await websocket.receive_text()
            await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        logger.info(
            f"/ws/document-upload/{document_upload_id}/text-explanation  --  Connection for explain text socket of document_upload={document_upload_id} disconnected"
        )
    finally:
        await websocket_manager.disconnect(document_upload_id, "summary")


@router.websocket("/ws/document-upload/{document_upload_id}/chat")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    document_upload_id: str,
    websocket_manager: WebSocketManager = Depends(get_websocket_manager),
    logger: logging.Logger = Depends(get_logger),
):
    await websocket_manager.connect(websocket, document_upload_id, "chat")
    try:
        while True:
            # data = await websocket.receive_text()
            await websocket.receive_text()
            # Process the received data
    except WebSocketDisconnect:
        logger.info(
            f"/ws/document-upload/{document_upload_id}/chat  --  Connection for chat socket of document_upload={document_upload_id} disconnected"
        )
    finally:
        await websocket_manager.disconnect(document_upload_id, "summary")
