import asyncio
from typing import List, Dict, Tuple, Any, Union, TypedDict
import re
from pinecone import Pinecone, ServerlessSpec
from config.ai_models import ModelPairConfig
from services.embedding_generator import EmbeddingGenerator

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class ProcessedChunk(TypedDict):
    chunk_id: str
    text: str
    token_count: int
    embedding: List[Union[float, str]]

class DocumentProcessor:
    def __init__(self, openai_api_key: str, pinecone_api_key: str, model_pair_config: ModelPairConfig):
        self.model_pair_config = model_pair_config
        self.embedding_generator = EmbeddingGenerator(
            openai_api_key, 
            model_pair_config['embedding_model']['model_name']
        )
        self.pinecone_client = Pinecone(api_key=pinecone_api_key)
        self.index_name = model_pair_config['pinecone']['index_name']
        self.ensure_pinecone_index()

    def ensure_pinecone_index(self):
        if self.index_name not in self.pinecone_client.list_indexes().names():
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=self.model_pair_config['embedding_model']['dimension'],
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1")
            )
        self.index = self.pinecone_client.Index(self.index_name)

    async def process_document(self, document: str, document_id: str) -> List[ProcessedChunk]:
        chunks = await self.chunk_text(document)
        return await self.process_chunks(chunks, document_id)

    async def chunk_text(self, text: str) -> List[Tuple[str, int]]:
        text = self._preprocess_text(text)
        text_chunks = self._split_text(text)
        chunks: List[Tuple[str, int]] = []
        current_chunk = ""
        current_token_count = 0

        for text_chunk in text_chunks:
            chunk_tokens = self.embedding_generator.num_tokens_from_string(text_chunk)
            
            if current_token_count + chunk_tokens > self.model_pair_config['processing']['max_tokens_per_chunk']:
                if current_chunk:
                    chunks.append((current_chunk, current_token_count))
                    logger.info(f"Created chunk with {current_token_count} tokens")
                    
                    # Calculate overlap
                    overlap_text = current_chunk.split()[-self.model_pair_config['processing']['overlap']:]
                    current_chunk = " ".join(overlap_text) + " " + text_chunk
                    current_token_count = self.embedding_generator.num_tokens_from_string(current_chunk)
                else:
                    # If a single text_chunk exceeds max_tokens_per_chunk, we need to split it
                    current_chunk = text_chunk[:self.model_pair_config['processing']['max_tokens_per_chunk']]
                    chunks.append((current_chunk, self.model_pair_config['processing']['max_tokens_per_chunk']))
                    logger.info(f"Created chunk with {self.model_pair_config['processing']['max_tokens_per_chunk']} tokens (split large chunk)")
                    current_chunk = text_chunk[self.model_pair_config['processing']['max_tokens_per_chunk']:]
                    current_token_count = self.embedding_generator.num_tokens_from_string(current_chunk)
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

    def _split_text(self, text: str) -> List[str]:
        chunks = text.split('\n')
        result: List[str] = []
        for chunk in chunks:
            if len(chunk) <= self.model_pair_config['processing']['chunk_size']:
                result.append(chunk)
            else:
                sentences = self._split_into_sentences(chunk)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= self.model_pair_config['processing']['chunk_size']:
                        current_chunk += " " + sentence if current_chunk else sentence
                    else:
                        if current_chunk:
                            result.append(current_chunk.strip())
                        if len(sentence) > self.model_pair_config['processing']['chunk_size']:
                            result.extend([sentence[i:i+self.model_pair_config['processing']['chunk_size']] for i in range(0, len(sentence), self.model_pair_config['processing']['chunk_size'])])
                        else:
                            current_chunk = sentence
                if current_chunk:
                    result.append(current_chunk.strip())
        return result

    async def process_chunks(self, chunks: List[Tuple[str, int]], document_id: str) -> List[ProcessedChunk]:
        chunk_texts = [chunk[0] for chunk in chunks]
        token_counts = [chunk[1] for chunk in chunks]

        embeddings = await self.embedding_generator.generate_embeddings_batch(chunk_texts)

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
                embedding=embedding[:5] + ['...']
            ))

        batch_size = 100  # You might want to add this to model_pair_config['processing'] as well
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i:i+batch_size]
            await asyncio.to_thread(self.index.upsert, vectors=batch)

        return processed_chunks