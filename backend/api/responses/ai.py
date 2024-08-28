from typing import Optional, List
from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    message_id: str
    content: str
    role: str
    created_at: str
    conversation_id: str


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    next_before: Optional[str]
