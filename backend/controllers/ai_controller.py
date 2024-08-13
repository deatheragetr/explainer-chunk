from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.ai_service import AIService
from services.document_service import DocumentService

router = APIRouter()

class SummarizeRequest(BaseModel):
    model: str

class ExplainRequest(BaseModel):
    highlight_text: str
    model: str

class ChatRequest(BaseModel):
    message: str
    model: str

@router.post("/documents/{document_id}/summary")
async def create_summary(document_id: str, request: SummarizeRequest, 
                         ai_service: AIService = Depends(),
                         document_service: DocumentService = Depends()):
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await ai_service.create_summary(document_id, document.content, request.model)
    return {"message": "Summary task started"}

@router.post("/documents/{document_id}/explanation")
async def create_explanation(document_id: str, request: ExplainRequest,
                             ai_service: AIService = Depends(),
                             document_service: DocumentService = Depends()):
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await ai_service.create_explanation(document_id, document.content, request.highlight_text, request.model)
    return {"message": "Explanation task started"}

@router.post("/documents/{document_id}/chat")
async def create_chat_message(document_id: str, request: ChatRequest,
                              ai_service: AIService = Depends(),
                              document_service: DocumentService = Depends()):
    document = await document_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    await ai_service.create_chat_response(document_id, document.content, request.message, request.model)
    return {"message": "Chat task started"}
