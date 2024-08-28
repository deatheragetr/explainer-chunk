from bson import ObjectId
from typing import Optional, Dict, Any, List
from config.ai_models import ModelPairConfig, DEFAULT_MODEL_CONFIGS, ModelName
from config.mongo import TypedAsyncIOMotorDatabase, AsyncIOMotorCollection
from db.models.document_uploads import (
    MongoDocumentUpload,
    ChatReference,
    OpenAIAssistantDetails,
)
from db.models.chat import (
    MongoChat,
    ChatMessageRole,
    create_chat,
    create_chat_message,
    create_conversation,
    MongoConversation,
)
from utils.progress_updater import ProgressUpdater
from services.openai_assistant_service import (
    OpenAIAssistantService,
    OpenAIAssistantError,
)
from fastapi import HTTPException

from config.logger import get_logger

logger = get_logger()


class AIChatService:
    def __init__(
        self,
        openai_api_key: str,
        model_pair_config: ModelPairConfig,
        progress_updater: ProgressUpdater,
        db: TypedAsyncIOMotorDatabase,
    ):
        self.model_pair_config = model_pair_config
        self.progress_updater = progress_updater
        self.openai_assistant_service = OpenAIAssistantService(
            openai_api_key=openai_api_key
        )
        self.db = db
        self.chat_collection: AsyncIOMotorCollection[MongoChat] = self.db.chats
        self.document_upoload_collection: AsyncIOMotorCollection[
            MongoDocumentUpload
        ] = self.db.document_uploads

    async def _get_document(self, document_upload_id: str) -> MongoDocumentUpload:
        obj_id = ObjectId(document_upload_id)
        document = await self.db.document_uploads.find_one({"_id": obj_id})
        if not document:
            raise ValueError(f"Document with ID {document_upload_id} not found")
        return document

    async def _ensure_assistant_exists(
        self, document: MongoDocumentUpload, model_name: ModelName
    ) -> OpenAIAssistantDetails:
        assistant = next(
            (
                a
                for a in document.get("openai_assistants", [])
                if a["model"] == model_name
            ),
            None,
        )
        if not assistant:
            assistant_details = (
                await self.openai_assistant_service.create_assistant_thread(
                    model_config=DEFAULT_MODEL_CONFIGS[model_name],
                    document=document,
                    mongo_collection=self.db.document_uploads,
                )
            )
            await self.db.document_uploads.update_one(
                {"_id": document["_id"]},
                {"$push": {"openai_assistants": assistant_details}},
            )
            return assistant_details
        return assistant

    async def _ensure_chat_exists(
        self,
        document: MongoDocumentUpload,
        assistant: OpenAIAssistantDetails,
    ) -> MongoChat:
        chat_ref = next(
            (
                c
                for c in document.get("chats", [])
                if c["model_name"] == assistant["model"]
            ),
            None,
        )
        chat = None
        if chat_ref:
            chat = await self.db.chats.find_one(
                {"_id": ObjectId(chat_ref["chat_id"])}, {"messages": 0}
            )

        if not chat_ref or not chat:
            # If chat_ref exists but chat doesn't, remove the orphaned reference
            if chat_ref and not chat:
                await self.db.document_uploads.update_one(
                    {"_id": document["_id"]},
                    {"$pull": {"chats": {"chat_id": chat_ref["chat_id"]}}},
                )
                logger.warning(
                    f"Removed orphaned chat reference for document {document['_id']}"
                )

            open_ai_assistant_details = (
                await (
                    self.openai_assistant_service.create_chat_thread(
                        model_config=self.model_pair_config, document=document
                    )
                )
            )
            new_chat = create_chat(
                document_upload=document,
                model_name=self.model_pair_config["model_name"],
                open_ai_assistant=open_ai_assistant_details,
            )
            result = await self.db.chats.insert_one(new_chat)
            chat_id = result.inserted_id
            chat_ref = ChatReference(
                chat_id=chat_id, model_name=self.model_pair_config["model_name"]
            )
            await self.db.document_uploads.update_one(
                {"_id": document["_id"]}, {"$push": {"chats": chat_ref}}
            )
            return new_chat
        return chat

    async def _get_or_create_conversation(self, chat: MongoChat) -> MongoConversation:
        active_conversation = next(
            (c for c in chat.get("conversations", []) if c["end_time"] is None), None
        )
        if active_conversation:
            return active_conversation

        new_conversation = create_conversation(
            open_ai_assistant=chat["open_ai_assistant"]
        )
        await self.db.chats.update_one(
            {"_id": chat["_id"]}, {"$push": {"conversations": new_conversation}}
        )
        return new_conversation

    async def _add_message_to_chat(
        self,
        chat: MongoChat,
        content: str,
        role: ChatMessageRole,
        conversation: MongoConversation,
    ) -> None:
        message = create_chat_message(content, role, conversation["_id"])
        await self.db.chats.update_one(
            {"_id": chat["_id"]}, {"$push": {"messages": message}}
        )

    async def send_chat_message(
        self,
        document_upload_id: str,
        message_content: str,
    ) -> Dict[str, Any]:
        document = await self._get_document(document_upload_id)

        # Ensure assistant exists
        assistant = await self._ensure_assistant_exists(
            document, self.model_pair_config["model_name"]
        )

        # Ensure chat exists
        chat = await self._ensure_chat_exists(document, assistant)

        conversation = await self._get_or_create_conversation(chat=chat)

        # Add user message to chat
        await self._add_message_to_chat(
            chat=chat,
            content=message_content,
            role=ChatMessageRole.USER,
            conversation=conversation,
        )

        # Send message to OpenAI
        await self.openai_assistant_service.add_message_to_thread(
            thread_id=conversation["open_ai_assistant"]["thread_id"],
            content=message_content,
        )

        try:
            full_text = ""
            async for text_chunk in self.openai_assistant_service.run_assistant(
                thread_id=conversation["open_ai_assistant"]["thread_id"],
                assistant_id=conversation["open_ai_assistant"]["assistant_id"],
                context_file_id=conversation["open_ai_assistant"][
                    "external_document_upload_id"
                ],
            ):
                full_text += text_chunk
                await self.progress_updater.update(
                    progress=50,  # You may want to calculate a more accurate progress
                    status="IN_PROGRESS",
                    payload={
                        "newText": text_chunk,
                    },
                )

            # Add assistant's response to chat
            await self._add_message_to_chat(
                chat=chat,
                content=full_text,
                role=ChatMessageRole.ASSISTANT,
                conversation=conversation,
            )

            await self.progress_updater.complete(payload={"completeText": full_text})

        except OpenAIAssistantError as e:
            logger.error(f"An error occurred: {str(e)}")
            await self.progress_updater.error()
            raise HTTPException(status_code=500, detail=str(e))

        return {
            "chat_id": str(chat["_id"]),
            "conversation_id": str(conversation["_id"]),
            "assistant_response": full_text,
        }

    # async def reset_conversation(self, document_upload_id: str) -> Dict[str, Any]:
    #     document = await self._get_document(document_upload_id)
    #     chat_id = await self._ensure_chat_exists(document)

    #     # End the current conversation if it exists
    #     await self.db.chats.update_one(
    #         {"_id": chat_id, "conversations.end_time": None},
    #         {"$set": {"conversations.$.end_time": datetime.now(UTC)}},
    #     )

    #     # Create a new thread in OpenAI
    #     thread_id = await self.openai_assistant_service.create_thread()

    #     # Get the assistant ID
    #     assistant_id = await self._ensure_assistant_exists(document)

    #     # Create a new conversation
    #     new_conversation_id = await self._get_or_create_conversation(
    #         chat_id, assistant_id, thread_id
    #     )

    #     return {
    #         "chat_id": str(chat_id),
    #         "new_conversation_id": str(new_conversation_id),
    #         "message": "Conversation reset successfully",
    #     }

    async def get_chat_history(
        self,
        document_upload_id: str,
        limit: int = 50,
        before_message_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        document = await self._get_document(document_upload_id)
        chat_ref = next(
            (
                c
                for c in document.get("chats", [])
                if c["model_name"] == self.model_pair_config["model_name"]
            ),
            None,
        )
        if not chat_ref:
            return []

        chat_id = chat_ref["chat_id"]
        query = {"_id": chat_id}
        if before_message_id:
            query["messages"] = {"$lt": ObjectId(before_message_id)}

        chat = await self.db.chats.find_one(query, {"messages": {"$slice": -limit}})

        if not chat:
            return []

        return [
            {
                "message_id": str(msg["_id"]),
                "content": msg["content"],
                "role": msg["role"],
                "created_at": msg["created_at"].isoformat(),
                "conversation_id": str(msg["conversation_id"]),
            }
            for msg in reversed(chat.get("messages", []))
        ]
