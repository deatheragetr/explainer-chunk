from pydantic import BaseModel
import tiktoken
from openai import AsyncOpenAI
from openai.types import CreateEmbeddingResponse
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Tuple, Any, Union, TypedDict
import re
import asyncio
from config.huey import huey

class ProcessedChunk(TypedDict):
    chunk_id: str
    text: str
    token_count: int
    embedding: List[Union[float, str]]  # Can be a list of floats or a list with floats and '...'


class DocumentProcessor:
    def __init__(self, openai_api_key: str, pinecone_api_key: str, index_name: str):
        self.embedding_generator = EmbeddingGenerator(openai_api_key)
        self.pinecone_client = Pinecone(api_key=pinecone_api_key)
        self.index_name = index_name
        self.ensure_pinecone_index()

    def ensure_pinecone_index(self):
        if self.index_name not in self.pinecone_client.list_indexes().names():
            print("Index NAME: ", self.index_name)
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=1536,  # Dimension for text-embedding-3-small
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pinecone_client.Index(self.index_name)

    async def process_document(self, document: str, document_id: str, max_tokens: int = 512, overlap: int = 50) -> List[ProcessedChunk]:
        chunks = await self.chunk_text(document, max_tokens, overlap)
        return await self.process_chunks(chunks, document_id)

    async def chunk_text(self, text: str, max_tokens: int = 512, overlap: int = 50) -> List[Tuple[str, int]]:
        text = self._preprocess_text(text)
        text_chunks = self._split_text(text)
        chunks: List[Tuple[str, int]] = []
        current_chunk = ""
        current_token_count = 0

        for text_chunk in text_chunks:
            chunk_tokens = await self.embedding_generator.num_tokens_from_string(text_chunk)
            
            if current_token_count + chunk_tokens > max_tokens:
                if current_chunk:
                    chunks.append((current_chunk, current_token_count))
                    logger.info(f"Created chunk with {current_token_count} tokens")
                    
                    # Calculate overlap
                    overlap_text = current_chunk.split()[-overlap:]
                    current_chunk = " ".join(overlap_text) + " " + text_chunk
                    current_token_count = await self.embedding_generator.num_tokens_from_string(current_chunk)
                else:
                    # If a single text_chunk exceeds max_tokens, we need to split it
                    current_chunk = text_chunk[:max_tokens]  # This is a simplification, ideally we'd split on word boundaries
                    chunks.append((current_chunk, max_tokens))
                    logger.info(f"Created chunk with {max_tokens} tokens (split large chunk)")
                    current_chunk = text_chunk[max_tokens:]
                    current_token_count = await self.embedding_generator.num_tokens_from_string(current_chunk)
            else:
                current_chunk += " " + text_chunk if current_chunk else text_chunk
                current_token_count += chunk_tokens

        if current_chunk:
            chunks.append((current_chunk, current_token_count))
            logger.info(f"Created final chunk with {current_token_count} tokens")

        logger.info(f"Total chunks created: {len(chunks)}")
        return chunks



    def _preprocess_text(self, text: str) -> str:
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def _split_into_sentences(self, text: str) -> List[str]:
        return re.split(r'(?<=[.!?])\s+', text)

    def _split_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """
        Split the text into chunks, trying to respect sentence boundaries where possible,
        but falling back to character-based splitting if necessary.
        """
        # First, try to split by newlines
        chunks = text.split('\n')
        
        # If any chunk is still too large, split it further
        result: List[str] = []
        for chunk in chunks:
            if len(chunk) <= chunk_size:
                result.append(chunk)
            else:
                # Try to split by sentence
                sentences = self._split_into_sentences(chunk)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= chunk_size:
                        current_chunk += " " + sentence if current_chunk else sentence
                    else:
                        if current_chunk:
                            result.append(current_chunk.strip())
                        # If the sentence itself is too long, split it by characters
                        if len(sentence) > chunk_size:
                            result.extend([sentence[i:i+chunk_size] for i in range(0, len(sentence), chunk_size)])
                        else:
                            current_chunk = sentence
                if current_chunk:
                    result.append(current_chunk.strip())
        
        return result


    async def _get_overlap(self, chunk: List[str], overlap: int) -> str:
        overlap_text = " ".join(chunk[-3:])
        while await self.embedding_generator.num_tokens_from_string(overlap_text) < overlap and len(chunk) > 3:
            chunk.pop(0)
            overlap_text = " ".join(chunk)
        return overlap_text

    async def process_chunks(self, chunks: List[Tuple[str, int]], document_id: str) -> List[ProcessedChunk]:
        chunk_texts = [chunk[0] for chunk in chunks]
        token_counts = [chunk[1] for chunk in chunks]

        # Generate embeddings in batches
        embeddings = await self.embedding_generator.generate_embeddings_batch(chunk_texts)

        # Prepare data for Pinecone upsert
        vectors: List[Dict[str, Any]] = []
        processed_chunks: List[ProcessedChunk] = []

        for i, (chunk_text, token_count, embedding) in enumerate(zip(chunk_texts, token_counts, embeddings)):
            chunk_id = f"{document_id}_chunk_{i}"
            metadata = {
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk_text,
                "token_count": token_count
            }
            vectors.append({
                "id": chunk_id,
                "values": embedding,
                "metadata": metadata
            })
            processed_chunks.append(ProcessedChunk(
                chunk_id=chunk_id,
                text=chunk_text,
                token_count=token_count,
                embedding=embedding[:5] + ['...']  # Truncated for brevity
            ))

        # Upsert to Pinecone in batches
        batch_size = 100  # Adjust based on Pinecone's limits and your needs
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            await asyncio.to_thread(self.index.upsert, vectors=batch)

        return processed_chunks


    async def query_similar_chunks(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = await self.embedding_generator.generate_embeddings_batch([query])
        results = await asyncio.to_thread(self.index.query, vector=query_embedding[0], top_k=top_k, include_metadata=True)
        return [
            {
                "chunk_id": match["id"],
                "score": match["score"],
                "text": match["metadata"]["text"],
                "document_id": match["metadata"]["document_id"],
                "chunk_index": match["metadata"]["chunk_index"]
            }
            for match in results["matches"]
        ]

class EmbeddingGenerator:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.encoding = tiktoken.encoding_for_model(model)

    async def num_tokens_from_string(self, string: str) -> int:
        return len(self.encoding.encode(string))

    async def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            response: CreateEmbeddingResponse = await self.openai_client.embeddings.create(model=self.model, input=batch)
            all_embeddings.extend([data.embedding for data in response.data])
        return all_embeddings


# Pydantic models for request and response
class DocumentRequest(BaseModel):
    document: str
    document_id: str

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


import logging
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    # filename="capture_website.log",
)
logger = logging.getLogger(__name__)

MODEL_CONFIGS = {
    "text-embedding-3-small": {
        "max_tokens": 512,
        "overlap": 50,
        "dimension": 1536,
        "index_name": "text-embedding-3-small-v1"
    }
}

from config.environment import PineconeSettings, OpenAISettings

pinecone_settings = PineconeSettings()
open_ai_settings = OpenAISettings()

@huey.task()
def process_document(input_text: str, document_id: str):
    logger.info(f"Queueing process document for document_id={document_id}")
    # Initialize DocumentProcessor
    try:
        processor = DocumentProcessor(
            openai_api_key=open_ai_settings.openai_api_key,
            pinecone_api_key=pinecone_settings.pinecone_api_key,
            # pinecone_environment="your-pinecone-environment",
            index_name=MODEL_CONFIGS["text-embedding-3-small"]["index_name"]
        )
        asyncio.run(processor.process_document(input_text, document_id))
        logger.info(f"Finished procssing document for document_id={document_id}")
    except Exception as e:
        logger.exception(f"Error in processing document for document_id={document_id}: {str(e)}")
        raise  # Re-raise the exception so Huey marks the task as failed