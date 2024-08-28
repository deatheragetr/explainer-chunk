from datetime import datetime, UTC
from typing import TypedDict, Annotated, List, Optional
from bson import ObjectId
from enum import Enum
from config.ai_models import ModelName
from db.models.document_uploads import MongoDocumentUpload


class ChatMessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MongoChatMessage(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    content: Annotated[str, "Content of the message"]
    role: Annotated[ChatMessageRole, "Role of the message sender"]
    created_at: Annotated[datetime, "Timestamp of the message"]
    conversation_id: Annotated[
        ObjectId, "ID of the conversation this message belongs to"
    ]


class OpenAIAssistantChat(TypedDict):
    assistant_id: Annotated[str, "OpenAI Assistant ID"]
    thread_id: Annotated[str, "OpenAI Thread ID"]
    external_document_upload_id: Optional[
        Annotated[
            str, "ID of the associated document upload, e.g., the file ID from OpenAI"
        ]
    ]


class MongoConversation(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    start_time: Annotated[datetime, "Start time of the conversation"]
    end_time: Optional[Annotated[datetime, "End time of the conversation"]]
    open_ai_assistant: Optional[
        Annotated[OpenAIAssistantChat, "Details about open ai config if applicable"]
    ]


class MongoChat(TypedDict):
    _id: Annotated[ObjectId, "MongoDB ObjectId"]
    document_upload_id: Annotated[ObjectId, "Reference to the associated document"]
    model_name: Annotated[ModelName, "Name of the model used for this chat"]
    open_ai_assistant: Optional[
        Annotated[OpenAIAssistantChat, "Details about open ai config if applicable"]
    ]
    conversations: Annotated[
        List[MongoConversation], "List of conversations in this chat"
    ]
    messages: Annotated[
        List[MongoChatMessage], "List of all chat messages across all conversations"
    ]


def create_chat(
    document_upload: MongoDocumentUpload,
    open_ai_assistant: OpenAIAssistantChat,
    model_name: ModelName,
) -> MongoChat:
    return MongoChat(
        _id=ObjectId(),
        document_upload_id=document_upload["_id"],
        open_ai_assistant=open_ai_assistant,
        model_name=model_name,
        conversations=[],
        messages=[],
    )


def create_conversation(
    open_ai_assistant: OpenAIAssistantChat | None,
    start_time: datetime = datetime.now(UTC),
):
    return MongoConversation(
        _id=ObjectId(),
        start_time=start_time,
        end_time=None,
        open_ai_assistant=open_ai_assistant,
    )


def create_chat_message(
    content: str, role: ChatMessageRole, conversation_id: ObjectId
) -> MongoChatMessage:
    return MongoChatMessage(
        _id=ObjectId(),
        content=content,
        role=role,
        created_at=datetime.now(UTC),
        conversation_id=conversation_id,
    )
    # created_at=datetime.now(UTC),
