from bson import ObjectId
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from config.mongo import get_db, TypedAsyncIOMotorDatabase
from config.ai_models import ModelName
from motor.motor_asyncio import AsyncIOMotorCollection
from db.models.document_uploads import MongoDocumentUpload
from services.chat_message_service import ChatMessageService
from background.huey_jobs.summarize_document_job import summarize_document
from background.huey_jobs.explain_text_job import explain_text
from background.huey_jobs.chat_job import chat_with_rag
from api.requests.ai import SummarizeRequest, ExplainRequest, ChatRequest
from api.responses.ai import ChatHistoryResponse, ChatMessageResponse

router = APIRouter()


@router.post("/documents/{document_upload_id}/summary")
async def create_summary(
    document_upload_id: str,
    request: SummarizeRequest,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
):
    # Convert string to ObjectId
    obj_id = ObjectId(document_upload_id)

    # Retrieve document from MongoDB
    collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
    # Avoid fetching the entire document, with the potentially long extracted text
    document = await collection.find_one({"_id": obj_id}, {"_id": 1, "file_details": 1})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    summarize_document(document_upload_id=document_upload_id, model_name=request.model)
    return {"message": "Summary task started"}


@router.post("/documents/{document_upload_id}/explanation")
async def create_explanation(
    document_upload_id: str,
    request: ExplainRequest,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
):
    obj_id = ObjectId(document_upload_id)

    # Retrieve document from MongoDB
    collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
    # Avoid fetching the entire document, with the potentially long extracted text
    document = await collection.find_one({"_id": obj_id}, {"_id": 1, "file_details": 1})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    explain_text(
        document_upload_id=document_upload_id,
        highlighted_text=request.highlighted_text,
        model_name=request.model,
    )
    return {"message": "Explanation task started"}


@router.post("/documents/{document_upload_id}/chat/messages")
async def create_chat_message(
    document_upload_id: str,
    request: ChatRequest,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
):
    obj_id = ObjectId(document_upload_id)

    # Retrieve document from MongoDB
    collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
    # Avoid fetching the entire document, with the potentially long extracted text
    document = await collection.find_one({"_id": obj_id}, {"_id": 1, "file_details": 1})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chat_with_rag(
        document_upload_id=document_upload_id,
        message_content=request.message_content,
        model_name=request.model,
    )
    return {"message": "Chat task started"}


@router.get(
    "/documents/{document_upload_id}/chat/messages", response_model=ChatHistoryResponse
)
async def get_chat_messages(
    document_upload_id: str,
    model: ModelName,
    before: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
):
    obj_id = ObjectId(document_upload_id)

    # Retrieve document from MongoDB
    collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
    document = await collection.find_one({"_id": obj_id}, {"_id": 1})
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chat_service = ChatMessageService(
        db=db,
    )
    messages, next_before = await chat_service.get_chat_history(
        document_upload_id=document_upload_id, model=model, before=before, limit=limit
    )

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                message_id=str(msg["_id"]),
                content=msg["content"],
                role=msg["role"],
                created_at=msg["created_at"].isoformat(),
                conversation_id=str(msg["conversation_id"]),
            )
            for msg in messages
        ],
        next_before=next_before,
    )
