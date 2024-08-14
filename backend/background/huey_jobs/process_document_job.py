import asyncio
from config.huey import huey
from config.ai_models import DEFAULT_MODEL_CONFIGS, ModelPairConfig
from config.environment import PineconeSettings, OpenAISettings
from services.document_processor import DocumentProcessor

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

pinecone_settings = PineconeSettings()
open_ai_settings = OpenAISettings()

async def async_process_document(input_text: str, document_id: str, model_pair_config: ModelPairConfig):
    processor = DocumentProcessor(
        openai_api_key=open_ai_settings.openai_api_key,
        pinecone_api_key=pinecone_settings.pinecone_api_key,
        model_pair_config=model_pair_config
    )
    try:
        await processor.process_document(input_text, document_id)
    finally:
        # Ensure any async resources are properly closed
        await processor.embedding_generator.openai_client.close()
        # await processor.pinecone_client.close()
        # Add any other cleanup here if necessary

@huey.task()
def process_document(input_text: str, document_id: str, model_name: str = "gpt-4o-mini"):
    logger.info(f"Queueing process document for document_id={document_id}")
    try:
        model_pair_config = DEFAULT_MODEL_CONFIGS[model_name]
        
        # Create and run the event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_process_document(input_text, document_id, model_pair_config))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        
        logger.info(f"Finished processing document for document_id={document_id}")
    except Exception as e:
        logger.exception(f"Error in processing document for document_id={document_id}: {str(e)}")
        raise  # Re-raise the exception so Huey marks the task as failed
