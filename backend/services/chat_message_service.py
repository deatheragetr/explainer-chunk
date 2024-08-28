from bson import ObjectId
from datetime import datetime, UTC
from typing import Optional, Any, Dict, List
from config.mongo import TypedAsyncIOMotorDatabase, AsyncIOMotorCollection
from config.ai_models import ModelName
from db.models.chat import MongoChat, MongoChatMessage


class ChatMessageService:
    def __init__(
        self,
        db: TypedAsyncIOMotorDatabase,
    ):
        self.db = db
        self.chat_collection: AsyncIOMotorCollection[MongoChat] = self.db.chats

    async def get_chat_history(
        self,
        document_upload_id: str,
        model: ModelName,
        before: Optional[str],
        limit: int,
    ) -> tuple[List[MongoChatMessage], Optional[str]]:
        match_stage: Dict[str, Any] = {
            "document_upload_id": ObjectId(document_upload_id),
            "model_name": model,
        }

        if before:
            before_date = datetime.fromisoformat(before)
        else:
            # If no 'before' is provided, use the current time
            before_date = datetime.now(UTC)

        pipeline = [
            {"$match": match_stage},
            {"$unwind": "$messages"},
            {"$match": {"messages.created_at": {"$lt": before_date}}},
            {"$sort": {"messages.created_at": -1}},
            {
                "$limit": limit + 1
            },  # Fetch one extra to determine if there are more results
            {
                "$project": {
                    "_id": "$messages._id",
                    "content": "$messages.content",
                    "role": "$messages.role",
                    "created_at": "$messages.created_at",
                    "conversation_id": "$messages.conversation_id",
                }
            },
        ]

        results: List[MongoChatMessage] = await self.chat_collection.aggregate(
            pipeline
        ).to_list(length=None)

        messages = results[:limit]
        next_before = (
            results[limit]["created_at"].isoformat() if len(results) > limit else None
        )

        return messages, next_before
