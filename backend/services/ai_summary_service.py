import asyncio
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion
from typing import List, Dict, Any, Tuple, Optional
from pinecone import Pinecone, ServerlessSpec
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from numpy.typing import NDArray
from scipy.sparse import spmatrix

from config.ai_models import ModelPairConfig
from utils.progress_updater import ProgressUpdater, SummaryProgressData
from services.embedding_generator import EmbeddingGenerator
from tenacity import retry, stop_after_attempt, wait_random_exponential


import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AISummaryService:
    def __init__(
        self,
        openai_api_key: str,
        pinecone_api_key: str,
        model_pair_config: ModelPairConfig,
        progress_updater: ProgressUpdater,
    ):
        self.model_pair_config = model_pair_config
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.embedding_generator = EmbeddingGenerator(
            openai_api_key, model_pair_config["embedding_model"]["model_name"]
        )
        self.pinecone_client = Pinecone(api_key=pinecone_api_key)
        self.index_name = model_pair_config["pinecone"]["index_name"]
        self.ensure_pinecone_index()
        self.semaphore = asyncio.Semaphore(10)  # Limit to 10 concurrent API calls
        self.progress_updater = progress_updater

    def ensure_pinecone_index(self):
        if self.index_name not in self.pinecone_client.list_indexes().names():
            self.pinecone_client.create_index(
                name=self.index_name,
                dimension=self.model_pair_config["embedding_model"]["dimension"],
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        self.index = self.pinecone_client.Index(self.index_name)

    async def query_similar_chunks(
        self, query: str, document_id: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        query_embedding = await self.embedding_generator.generate_embeddings_batch(
            [query]
        )
        results = await asyncio.to_thread(
            self.index.query,
            vector=query_embedding[0],
            filter={"document_id": document_id},
            top_k=top_k,
            include_metadata=True,
        )
        return [
            {
                "chunk_id": match["id"],
                "score": match["score"],
                "text": match["metadata"]["text"],
                "document_id": match["metadata"]["document_id"],
                "chunk_index": match["metadata"]["chunk_index"],
            }
            for match in results["matches"]
        ]

    async def get_document_chunks(
        self, document_id: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        # Retrieve all chunks for the document, sorted by chunk_index
        results = await asyncio.to_thread(
            self.index.query,
            vector=[0]
            * self.model_pair_config["embedding_model"]["dimension"],  # Dummy vector
            filter={"document_id": document_id},
            top_k=top_k,
            include_metadata=True,
        )
        chunks = [
            {
                "chunk_id": match["id"],
                "text": match["metadata"]["text"],
                "document_id": match["metadata"]["document_id"],
                "chunk_index": match["metadata"]["chunk_index"],
            }
            for match in results["matches"]
        ]
        return sorted(chunks, key=lambda x: x["chunk_index"])

    # REMOVE?
    # async def basic_summarize_text(self, document_id: str) -> Dict[str, str]:
    #     chunks = await self.get_document_chunks(document_id, top_k=10)
    #     prompt = "Summarize the following document:\n\n"
    #     for chunk in chunks:
    #         prompt += chunk['text'] + "\n\n"

    #     response = await self.openai_client.chat.completions.create(
    #         model=self.model_pair_config['chat_model']['model_name'],
    #         messages=[
    #             {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
    #             {"role": "user", "content": prompt}
    #         ],
    #         max_tokens=self.model_pair_config['chat_model']['max_output_tokens']
    #     )

    #     summary_content = response.choices[0].message.content
    #     if summary_content is None:
    #         raise ValueError("Failed to generate summary: API returned None")

    #     return {"summary": summary_content}

    # REMOVE?
    # async def recursive_summarize(self, document_id: str) -> Dict[str, str]:
    #     chunks = await self.get_document_chunks(document_id, top_k=100)
    #     max_chunk_size = self.model_pair_config['processing']['max_tokens_per_chunk']

    #     async def summarize_chunk(chunk_text: str) -> str:
    #         response = await self.openai_client.chat.completions.create(
    #             model=self.model_pair_config['chat_model']['model_name'],
    #             messages=[
    #                 {"role": "system", "content": "Summarize the following text concisely:"},
    #                 {"role": "user", "content": chunk_text}
    #             ],
    #             max_tokens=self.model_pair_config['chat_model']['max_output_tokens'] // 2
    #         )
    #         return response.choices[0].message.content or ""

    #     # First level of summarization
    #     summaries: List[str] = []
    #     current_chunk = ""
    #     current_tokens = 0
    #     for chunk in chunks:
    #         chunk_tokens = self.embedding_generator.num_tokens_from_string(chunk['text'])
    #         if current_tokens + chunk_tokens > max_chunk_size:
    #             if current_chunk:
    #                 summaries.append(await summarize_chunk(current_chunk))
    #             current_chunk = chunk['text']
    #             current_tokens = chunk_tokens
    #         else:
    #             current_chunk += "\n" + chunk['text']
    #             current_tokens += chunk_tokens
    #     if current_chunk:
    #         summaries.append(await summarize_chunk(current_chunk))

    #     # Second level of summarization if needed
    #     total_tokens = self.embedding_generator.num_tokens_from_string('\n'.join(summaries))
    #     if total_tokens > max_chunk_size:
    #         final_summary = await summarize_chunk('\n'.join(summaries))
    #     else:
    #         final_summary = '\n'.join(summaries)

    #     print(final_summary)
    #     return {"summary": final_summary}

    @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
    async def _make_api_call(
        self, messages: List[ChatCompletionMessageParam], max_tokens: int
    ) -> str:
        response: ChatCompletion = await self.openai_client.chat.completions.create(
            model=self.model_pair_config["chat_model"]["model_name"],
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""

    async def most_advanced_summarize(self, document_id: str) -> Dict[str, Any]:
        chunks = await self.get_document_chunks(document_id, top_k=50)
        target_length = self.model_pair_config["chat_model"]["target_summary_length"]

        async def summarize_with_context(
            text: str, context: str = "", target_tokens: Optional[int] = None
        ) -> str:
            prompt = f"Context: {context}\n\nSummarize the following text concisely, maintaining coherence with the context. "
            if target_tokens:
                prompt += f"Aim for approximately {target_tokens} tokens."

            messages: List[ChatCompletionMessageParam] = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ]

            return await self._make_api_call(
                messages,
                target_tokens
                or self.model_pair_config["chat_model"]["max_output_tokens"],
            )

        async def rate_limited_summarize(
            chunk: str, context: str, target_tokens: Optional[int] = None
        ) -> str:
            async with self.semaphore:
                return await summarize_with_context(chunk, context, target_tokens)

        def calculate_importance(texts: List[str]) -> NDArray[np.float64]:
            vectorizer = TfidfVectorizer(max_features=1000)  # Limit features for speed
            tfidf_matrix: spmatrix = vectorizer.fit_transform(texts)
            tfidf_array: NDArray[np.float64] = tfidf_matrix.toarray()
            centroid: NDArray[np.float64] = np.mean(tfidf_array, axis=0)
            similarities: NDArray[np.float64] = cosine_similarity(
                tfidf_array, centroid.reshape(1, -1)
            )
            return similarities.flatten()

        async def adaptive_chunk(texts: List[str]) -> List[Tuple[str, float]]:
            if not texts:
                return []
            importances = calculate_importance(texts)
            sorted_chunks = sorted(
                zip(texts, importances), key=lambda x: x[1], reverse=True
            )

            result: List[Tuple[str, float]] = []
            current_chunk = ""
            current_tokens = 0

            for text, importance in sorted_chunks:
                text_tokens = self.embedding_generator.num_tokens_from_string(text)
                if (
                    current_tokens + text_tokens
                    > self.model_pair_config["processing"]["max_tokens_per_chunk"]
                ):
                    if current_chunk:
                        result.append((current_chunk, importance))
                    current_chunk = text
                    current_tokens = text_tokens
                else:
                    current_chunk += "\n" + text
                    current_tokens += text_tokens

            if current_chunk:
                result.append(
                    (current_chunk, importances[-1] if importances.size > 0 else 0.0)
                )

            return result

        # First level of summarization with adaptive chunking
        chunk_texts = [chunk["text"] for chunk in chunks]
        adaptive_chunks = await adaptive_chunk(chunk_texts)

        # Fully parallelized summarization with rate limiting
        summarization_tasks = [
            rate_limited_summarize(chunk[0], adaptive_chunks[i - 1][0] if i > 0 else "")
            for i, chunk in enumerate(adaptive_chunks)
        ]
        first_level_summaries = await asyncio.gather(*summarization_tasks)

        # Determine if we need a second level of summarization
        total_tokens = sum(
            self.embedding_generator.num_tokens_from_string(summary)
            for summary in first_level_summaries
        )
        if total_tokens > target_length:
            num_second_level_chunks = max(1, total_tokens // target_length)
            target_chunk_length = target_length // num_second_level_chunks

            second_level_chunks = await adaptive_chunk(first_level_summaries)
            summarization_tasks = [
                rate_limited_summarize(
                    chunk[0],
                    second_level_chunks[i - 1][0] if i > 0 else "",
                    target_chunk_length,
                )
                for i, chunk in enumerate(second_level_chunks)
            ]
            second_level_summaries = await asyncio.gather(*summarization_tasks)
            final_summary = "\n\n".join(second_level_summaries)
        else:
            final_summary = "\n\n".join(first_level_summaries)

        # Final condensation if still too long
        final_summary_tokens = self.embedding_generator.num_tokens_from_string(
            final_summary
        )
        if final_summary_tokens > target_length:
            final_summary = await summarize_with_context(
                final_summary, target_tokens=target_length
            )

        await self.progress_updater.complete(
            payload=SummaryProgressData(
                completeText=final_summary,
            )
        )

        return {
            "summary": final_summary,
            "metadata": {
                "original_chunks": len(chunks),
                "first_level_summaries": len(first_level_summaries),
                "final_summary_length": self.embedding_generator.num_tokens_from_string(
                    final_summary
                ),
                "target_summary_length": target_length,
                "model_used": self.model_pair_config["chat_model"]["model_name"],
            },
        }
