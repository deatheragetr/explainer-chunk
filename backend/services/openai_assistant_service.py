import os
import tempfile
from typing import Optional, AsyncGenerator, Dict, Any
from openai import OpenAI, AsyncOpenAI
from openai.types.file_object import FileObject
from openai.types.beta import Thread
from openai.types.beta.threads.message import Message
from openai.types.beta.threads.message_create_params import Attachment
from openai.types.beta.threads.run import Run
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from config.ai_models import ModelPairConfig
from db.models.document_uploads import MongoDocumentUpload, OpenAIAssistantDetails
from db.models.chat import OpenAIAssistantChat
from config.mongo import AsyncIOMotorCollection
from config.s3 import s3_client
from config.logger import get_logger
from utils.file_type_normalizer import mimetype_to_file_extension

logger = get_logger()


class OpenAIAssistantError(Exception):
    """Base class for OpenAI Assistant related errors"""


class ThreadCreationError(OpenAIAssistantError):
    """Raised when thread creation fails"""


class FileUploadError(OpenAIAssistantError):
    """Raised when file upload to OpenAI fails"""


class AssistantFileAttachmentError(OpenAIAssistantError):
    """Raised when attaching a file to an assistant fails"""


class MessageAdditionError(OpenAIAssistantError):
    """Raised when adding a message to a thread fails"""


class AssistantRunError(OpenAIAssistantError):
    """Raised when running an assistant fails"""


class OpenAIAssistantService:
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        self.async_client = AsyncOpenAI(api_key=openai_api_key)
        self.supported_file_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
            "application/json",
            "text/html",
            # Epub, CSV, Excel are not supported by OpenAI's Assistant API file tool
        }  # Add other supported types as needed

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(OpenAIAssistantError),
        reraise=True,
    )
    async def create_assistant_thread(
        self,
        model_config: ModelPairConfig,
        document: MongoDocumentUpload,
        mongo_collection: AsyncIOMotorCollection[MongoDocumentUpload],
    ) -> OpenAIAssistantDetails:
        assistant_id = model_config["assistant"]["id"]
        assistant_type = model_config["assistant"]["type"]
        if not assistant_id:
            raise ValueError("OpenAI Assistant ID not found in the model configuration")

        if assistant_type != "openai":
            raise ValueError(
                f"Assistant type '{assistant_type}' is not supported by this service"
            )

        try:
            # Create a new thread
            thread = self._create_thread()

            file_id = None
            file_type = document["file_details"]["file_type"]
            if file_type in self.supported_file_types:
                # Upload the file to OpenAI if it's a supported type
                file_path = await self._get_file_path(document)
                openai_file = self._upload_file(file_path, file_type)
                file_id = openai_file.id

                # Add the file to the assistant
                self._attach_file_to_thread(thread.id, file_id)
            else:
                # For unsupported file types, add the extracted text as a message
                extracted_text = document.get("extracted_text", "")
                if extracted_text:
                    await self.add_message_to_thread(
                        thread.id,
                        f"Document Content:\n\n{extracted_text[:1000]}...",  # Truncate if too long
                    )
                else:
                    logger.warning(
                        f"No extracted text available for unsupported file type: {document['file_details']['file_type']}"
                    )

            # Create OpenAIAssistantDetails
            assistant_details = OpenAIAssistantDetails(
                assistant_id=assistant_id,
                thread_id=thread.id,
                model=model_config["chat_model"]["model_name"],
                external_document_upload_id=file_id,
                last_message_id=None,
            )

            # Update the MongoDB document with the new AssistantDetails
            await mongo_collection.update_one(
                {"_id": document["_id"]},
                {"$push": {"openai_assistants": assistant_details}},
            )

            return assistant_details

        except Exception as e:
            logger.error(f"Error in create_chat {str(e)}")
            raise OpenAIAssistantError(
                f"Failed to create chat assistant thread: {str(e)}"
            ) from e

    async def create_chat_thread(
        self,
        model_config: ModelPairConfig,
        document: MongoDocumentUpload,
    ) -> OpenAIAssistantChat:
        assistant_id = model_config["assistant"]["id"]
        assistant_type = model_config["assistant"]["type"]
        if not assistant_id:
            raise ValueError("OpenAI Assistant ID not found in the model configuration")

        if assistant_type != "openai":
            raise ValueError(
                f"Assistant type '{assistant_type}' is not supported by this service"
            )

        try:
            # Create a new thread
            thread = self._create_thread()

            file_id = None
            file_type = document["file_details"]["file_type"]
            if file_type in self.supported_file_types:
                # Upload the file to OpenAI if it's a supported type
                file_path = await self._get_file_path(document)
                openai_file = self._upload_file(file_path, file_type)
                file_id = openai_file.id

                # Add the file to the assistant
                self._attach_file_to_thread(thread.id, file_id)
            else:
                # For unsupported file types, add the extracted text as a message
                extracted_text = document.get("extracted_text", "")
                if extracted_text:
                    await self.add_message_to_thread(
                        thread.id,
                        f"Document Content:\n\n{extracted_text[:1000]}...",  # Truncate if too long
                    )
                else:
                    logger.warning(
                        f"No extracted text available for unsupported file type: {document['file_details']['file_type']}"
                    )

            return OpenAIAssistantChat(
                assistant_id=assistant_id,
                thread_id=thread.id,
                external_document_upload_id=file_id,
            )
        except Exception as e:
            logger.error(f"Error in create_chat {str(e)}")
            raise OpenAIAssistantError(
                f"Failed to create chat assistant thread: {str(e)}"
            ) from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def _create_thread(self) -> Thread:
        try:
            return self.client.beta.threads.create()
        except Exception as e:
            logger.error(f"Error creating thread: {str(e)}")
            raise ThreadCreationError("Failed to create thread") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def _upload_file(self, file_path: str, file_type: str) -> FileObject:
        try:
            file_name = os.path.basename(file_path)
            file_extension = mimetype_to_file_extension.get(file_type)

            # OpenAI requires matching file extensions; Can't infer from mimetype
            if file_extension and not file_name.lower().endswith(file_extension):
                new_file_name = f"{file_name}{file_extension}"
                new_file_path = os.path.join(os.path.dirname(file_path), new_file_name)
                os.rename(file_path, new_file_path)
                file_path = new_file_path

            with open(file_path, "rb") as file:
                return self.client.files.create(file=file, purpose="assistants")
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise FileUploadError("Failed to upload file to OpenAI") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    def _attach_file_to_thread(self, thread_id: str, file_id: str) -> Message:
        try:
            return self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content="The file you the assistant will use in answering my questions",
                attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}],
            )
        except Exception as e:
            logger.error(f"Error attaching file to assistant: {str(e)}")
            raise AssistantFileAttachmentError(
                "Failed to attach file to assistant"
            ) from e

    async def _get_file_path(self, document: MongoDocumentUpload) -> str:
        file_key = document["file_details"]["file_key"]
        file_name = document["file_details"]["file_name"]

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_{file_name}"
        ) as temp_file:
            s3_client.download_fileobj(
                Bucket=document["file_details"]["s3_bucket"],
                Key=file_key,
                Fileobj=temp_file,
            )
            return temp_file.name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(MessageAdditionError),
        reraise=True,
    )
    async def add_message_to_thread(
        self, thread_id: str, content: str, file_ids: Optional[list[str]] = None
    ) -> Message:
        try:
            attachments = [
                Attachment(file_id=file_id, tools=[{"type": "file_search"}])
                for file_id in file_ids or []
            ]
            message = self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content,
                attachments=attachments,
            )
            return message
        except Exception as e:
            logger.error(f"Error adding message to thread: {str(e)}")
            raise MessageAdditionError("Failed to add message to thread") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(AssistantRunError),
        reraise=True,
    )
    async def run_assistant(
        self, thread_id: str, assistant_id: str, context_file_id: str
    ) -> AsyncGenerator[str, None]:

        instructions = (
            f"Use this uploaded file {context_file_id} to answer any questions"
        )
        try:
            with self.client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                instructions=instructions,
            ) as stream:
                for text in stream.text_deltas:
                    yield text

        except Exception as e:
            logger.error(f"Error running assistant: {str(e)}")

            raise AssistantRunError("Failed to run assistant") from e

    async def get_run_status(self, thread_id: str, run_id: str) -> Run:
        try:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )
            return run
        except Exception as e:
            logger.error(f"Error getting run status: {str(e)}")
            raise OpenAIAssistantError("Failed to get run status") from e

    async def get_messages(self, thread_id: str) -> list[Message]:
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            return messages.data
        except Exception as e:
            logger.error(f"Error getting messages: {str(e)}")
            raise OpenAIAssistantError("Failed to get messages") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(OpenAIAssistantError),
        reraise=True,
    )
    async def explain_text_subsection(
        self,
        thread_id: str,
        assistant_id: str,
        text_subsection: str,
        context_file_id: str,
        # reading_level: str = "intermediate",
        # reading_level: str = "in elementary school",
        reading_level: str = "a professional with postgraduate training in the field",
        output_length: str = "very short",
    ) -> AsyncGenerator[str, None]:
        # ) -> None:
        try:
            # Validate input parameters
            if not text_subsection.strip():
                raise ValueError("text_subsection must not be empty")

            if not context_file_id.strip():
                raise ValueError("context_file_id must not be empty")

            valid_reading_levels = [
                "in elementary school",
                "in middle school",
                "in high school",
                "in college",
                "in graduate school, but not in the field"
                "in graduate school and in the field",
                "a professional with postgraduate training in the field",
            ]
            # if reading_level not in valid_reading_levels:
            #     raise ValueError(
            #         f"Invalid reading_level. Must be one of {valid_reading_levels}"
            #     )

            valid_output_lengths = ["very short", "short", "medium", "long"]
            if output_length not in valid_output_lengths:
                raise ValueError(
                    f"Invalid output_length. Must be one of {valid_output_lengths}"
                )

            # Create instructions for the assistant
            instructions = f"""
            Answer this users questions about the following text subsection in the context of the file with ID {context_file_id}, addressing the person as though
            they have the reading level of someone who is {reading_level}.
            """

            # Add the message with the text subsection and context file ID to the thread
            message_content = f"""
            Please explain the following text subsection in the context of the file with ID {context_file_id}:

            "{text_subsection}"

            Adjust your explanation to the reading level of someone who is {reading_level}.
            Focus only on the content from the specified file (ID: {context_file_id}) when providing context and explanations.
            Please make your explanation concise.
            """

            await self.add_message_to_thread(
                thread_id=thread_id, content=message_content
            )

            # Run the assistant with streaming
            with self.client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant_id,
                instructions=instructions,
                # event_handler=handler,
            ) as stream:
                for text in stream.text_deltas:
                    yield text

        except Exception as e:
            logger.error(f"Error in explain_text_subsection: {str(e)}")
            raise OpenAIAssistantError(
                f"Failed to explain text subsection: {str(e)}"
            ) from e
