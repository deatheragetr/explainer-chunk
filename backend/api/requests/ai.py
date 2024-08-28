from pydantic import BaseModel
from config.ai_models import ModelName


class SummarizeRequest(BaseModel):
    model: ModelName


class ExplainRequest(BaseModel):
    highlighted_text: str
    model: ModelName


class ChatRequest(BaseModel):
    message_content: str
    model: ModelName
