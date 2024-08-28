from typing import Dict, TypedDict, Literal


class EmbeddingModelConfig(TypedDict):
    dimension: int
    model_name: str
    max_input_tokens: int  # Maximum tokens the embedding model can handle


class ChatModelConfig(TypedDict):
    model_name: str
    max_context_tokens: int  # Maximum tokens for context
    max_output_tokens: int  # Maximum tokens for output (completion)
    target_summary_length: int  # Target summary length in tokens.  Rule of thumb seems to be 1000 tokens ~ 750-850 English words.  However, this can vary a lot.


class ProcessingConfig(TypedDict):
    chunk_size: int  # in chars
    overlap: int  # in tokens
    max_tokens_per_chunk: int


class PineconeConfig(TypedDict):
    index_name: str


class AssistantConfig(TypedDict):
    type: str
    id: str


ModelName = Literal["gpt-4o-mini"]


class ModelPairConfig(TypedDict):
    model_name: ModelName
    embedding_model: EmbeddingModelConfig
    chat_model: ChatModelConfig
    processing: ProcessingConfig
    pinecone: PineconeConfig
    assistant: AssistantConfig


OPENAI_ASSISTANTS = {
    "gpt-4o-mini": {
        "assistant_id": "asst_nIvVttQMhsJYqJe3dDN5fHgf",
    }
}

MODEL_CONFIGS: Dict[str, ModelPairConfig] = {
    "text-embedding-3-small_gpt-4o-mini": {
        "model_name": "gpt-4o-mini",
        "embedding_model": {
            "dimension": 1536,  # https://platform.openai.com/docs/guides/embeddings/how-to-get-embeddings
            "model_name": "text-embedding-3-small",
            "max_input_tokens": 8191,  # https://platform.openai.com/docs/guides/embeddings/embedding-models
        },
        "chat_model": {
            "model_name": "gpt-4o-mini",
            "max_context_tokens": 128000,
            "max_output_tokens": 16000,
            "target_summary_length": 1000,
        },
        "assistant": {
            "type": "openai",
            "id": OPENAI_ASSISTANTS["gpt-4o-mini"]["assistant_id"],
        },
        "processing": {
            "chunk_size": 1000,  # Chunking max_tokens
            "max_tokens_per_chunk": 512,  # Chunking max_tokens
            "overlap": 50,
        },
        "pinecone": {"index_name": "text-embedding-3-small-v1"},
    }
}

DEFAULT_MODEL_CONFIGS: Dict[str, ModelPairConfig] = {
    "gpt-4o-mini": MODEL_CONFIGS["text-embedding-3-small_gpt-4o-mini"]
}


# MODEL_CONFIGS: Dict[str, ModelConfig] = {
#     "text-embedding-3-small": {
#         "max_tokens": 512,
#         "overlap": 50,
#         "dimension": 1536,
#         "index_name": "text-embedding-3-small-v1",
#         "chunk_size": 1000,
#         "model_name": "text-embedding-3-small"
#     }
# }
