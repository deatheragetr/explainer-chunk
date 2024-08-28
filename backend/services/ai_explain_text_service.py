from bson import ObjectId
from config.ai_models import ModelPairConfig
from config.mongo import TypedAsyncIOMotorDatabase, AsyncIOMotorCollection
from db.models.document_uploads import MongoDocumentUpload, find_assistant_by_model
from utils.progress_updater import ProgressUpdater
from services.openai_assistant_service import (
    OpenAIAssistantService,
    OpenAIAssistantError,
)

from config.logger import get_logger

logger = get_logger()


class AIExplainTextService:
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

    async def explain_text(
        self,
        document_upload_id: str,
        highlighted_text: str,
        model_pair_config: ModelPairConfig,
    ):

        obj_id = ObjectId(document_upload_id)
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = (
            self.db.document_uploads
        )
        document = await collection.find_one({"_id": obj_id})
        if not document:
            raise ValueError(
                f"AI Explain Text Service: Document with ID {document_upload_id} not found"
            )

        openai_assistant = find_assistant_by_model(
            document, model_pair_config["model_name"]
        )
        if openai_assistant is None:
            # TODO: Dynamically create assistant IF user has account access
            raise ValueError(
                f"AI Explain Text Service: Assistant with model {model_pair_config['model_name']} not found"
            )

        try:
            full_text = ""
            async for (
                text_chunk
            ) in self.openai_assistant_service.explain_text_subsection(
                thread_id=openai_assistant["thread_id"],
                assistant_id=openai_assistant["assistant_id"],
                text_subsection=highlighted_text,
                context_file_id=openai_assistant.get("external_document_upload_id")
                or "",
                reading_level="intermediate",
                output_length="medium",
            ):
                full_text += text_chunk
                await self.progress_updater.update(
                    progress=50,  # You may want to calculate a more accurate progress
                    status="IN_PROGRESS",
                    payload={
                        "newText": text_chunk,
                    },
                )

            await self.progress_updater.complete(payload={"completeText": full_text})

        except OpenAIAssistantError as e:
            logger.error(f"An error occurred: {str(e)}")
            await self.progress_updater.error()
            raise

        return "foo"
