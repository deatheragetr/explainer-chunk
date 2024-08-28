from typing import List
import tiktoken
from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse

class EmbeddingGenerator:
    def __init__(self, api_key: str, model: str):
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)

    def num_tokens_from_string(self, string: str) -> int:
        return len(self.encoding.encode(string))

    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            response: CreateEmbeddingResponse = await self.openai_client.embeddings.create(model=self.model, input=batch)
            all_embeddings.extend([data.embedding for data in response.data])
        return all_embeddings
