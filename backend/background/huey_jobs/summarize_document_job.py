import asyncio
from config.huey import huey
from config.ai_models import DEFAULT_MODEL_CONFIGS
from config.environment import PineconeSettings, OpenAISettings
from services.ai_summary_service import AISummaryService

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

pinecone_settings = PineconeSettings()
open_ai_settings = OpenAISettings()

@huey.task()
def summarize_document(document_id: str, model_name: str = "gpt-4o-mini"):
    logger.info(f"Queueing summarize document for document_id={document_id} for model={model_name}")
    try:
        model_config = DEFAULT_MODEL_CONFIGS[model_name]
        ai_summary_service = AISummaryService(
            openai_api_key=open_ai_settings.openai_api_key,
            pinecone_api_key=pinecone_settings.pinecone_api_key,
            model_pair_config=model_config
        )

        asyncio.run(ai_summary_service.most_advanced_summarize(document_id))
        logger.info(f"Finished summarizing document with document_id={document_id} for model={model_name}")
    except Exception as e:
        logger.exception(f"Error in summarizing document for document_id={document_id} for model={model_name}: {str(e)}")
        raise  # Re-raise the exception so Huey marks the task as failed