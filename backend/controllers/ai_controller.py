from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from config.mongo import get_db, TypedAsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from db.models.document_uploads import MongoDocumentUpload
from background.huey_jobs.summarize_document_job import summarize_document

router = APIRouter()


class SummarizeRequest(BaseModel):
    model: str


class ExplainRequest(BaseModel):
    highlight_text: str
    model: str


class ChatRequest(BaseModel):
    message: str
    model: str


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

    summarize_document(document_id=document_upload_id, model_name=request.model)
    return {"message": "Summary task started"}


# @router.post("/documents/{document_id}/explanation")
# async def create_explanation(document_id: str, request: ExplainRequest,
#                              ai_service: AIService = Depends(),
#                              document_service: DocumentService = Depends()):
#     document = await document_service.get_document(document_id)
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
#     await ai_service.create_explanation(document_id, document.content, request.highlight_text, request.model)
#     return {"message": "Explanation task started"}

# @router.post("/documents/{document_id}/chat")
# async def create_chat_message(document_id: str, request: ChatRequest,
#                               ai_service: AIService = Depends(),
#                               document_service: DocumentService = Depends()):
#     document = await document_service.get_document(document_id)
#     if not document:
#         raise HTTPException(status_code=404, detail="Document not found")
#     await ai_service.create_chat_response(document_id, document.content, request.message, request.model)
#     return {"message": "Chat task started"}
