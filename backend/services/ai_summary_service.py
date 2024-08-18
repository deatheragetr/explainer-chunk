import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorCollection
from bson import ObjectId
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion import ChatCompletion
from typing import List, Dict, Any, Tuple, Optional, Coroutine
from pinecone import Pinecone, ServerlessSpec
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from numpy.typing import NDArray
from scipy.sparse import spmatrix

from config.ai_models import ModelPairConfig
from config.mongo import TypedAsyncIOMotorDatabase
from db.models.document_uploads import (
    MongoDocumentUpload,
)
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

    async def basic_summarize_text(self, document_id: str) -> Dict[str, str]:
        chunks = await self.get_document_chunks(document_id, top_k=20)
        prompt = "This is the document.  Keep in mind, this may be the whole document, or a fragment of it.  Please try to summarize the document as a whole the best you can:\n\n"
        for chunk in chunks:
            prompt += chunk["text"] + "\n\n"

        response = await self.openai_client.chat.completions.create(
            model=self.model_pair_config["chat_model"]["model_name"],
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes documents.  I'm providing you with as much of the document as I can fit in this message, possibly the whole thing if it fits. Please summarize it for me.  Please describe the type of document, its purpose and give an intelligible summary of it",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.model_pair_config["chat_model"]["max_output_tokens"],
        )

        summary_content = response.choices[0].message.content
        if summary_content is None:
            raise ValueError("Failed to generate summary: API returned None")

        await self.progress_updater.complete(
            payload=SummaryProgressData(
                completeText=summary_content,
            )
        )
        return {"summary": summary_content}

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

        await self.progress_updater.update(progress=5, status="IN_PROGRESS")

        async def summarize_with_context(
            text: str, context: str = "", target_tokens: Optional[int] = None
        ) -> str:
            prompt = f"Context: {context}\n\nSummarize the following text concisely, maintaining coherence with the context. Please provide the purpose, key points, and any other relevant information to understanding the document as a cohesive whole.  Be intelligible.\n\n"
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

        await self.progress_updater.update(progress=10, status="IN_PROGRESS")

        # Fully parallelized summarization with rate limiting
        summarization_tasks: List[Coroutine[Any, Any, str]] = []
        for i, chunk in enumerate(adaptive_chunks):
            summarization_tasks.append(
                rate_limited_summarize(
                    chunk[0], adaptive_chunks[i - 1][0] if i > 0 else ""
                )
            )
            # Update progress for each chunk
            await self.progress_updater.update(
                progress=10 + (30 * (i + 1) / len(adaptive_chunks)),
                status="IN_PROGRESS",
            )

        first_level_summaries = await asyncio.gather(*summarization_tasks)

        await self.progress_updater.update(progress=40, status="IN_PROGRESS")

        # Determine if we need a second level of summarization
        total_tokens = sum(
            self.embedding_generator.num_tokens_from_string(summary)
            for summary in first_level_summaries
        )
        if total_tokens > target_length:
            num_second_level_chunks = max(1, total_tokens // target_length)
            target_chunk_length = target_length // num_second_level_chunks

            second_level_chunks = await adaptive_chunk(first_level_summaries)
            summarization_tasks: List[Coroutine[Any, Any, str]] = []
            for i, chunk in enumerate(second_level_chunks):
                summarization_tasks.append(
                    rate_limited_summarize(
                        chunk[0],
                        second_level_chunks[i - 1][0] if i > 0 else "",
                        target_chunk_length,
                    )
                )
                await self.progress_updater.update(
                    progress=40 + (30 * (i + 1) / len(second_level_chunks)),
                    status="IN_PROGRESS",
                )

            second_level_summaries = await asyncio.gather(*summarization_tasks)
            final_summary = "\n\n".join(second_level_summaries)
        else:
            final_summary = "\n\n".join(first_level_summaries)

        await self.progress_updater.update(progress=70, status="IN_PROGRESS")

        # Final condensation if still too long
        final_summary_tokens = self.embedding_generator.num_tokens_from_string(
            final_summary
        )
        if final_summary_tokens > target_length:
            final_summary = await summarize_with_context(
                final_summary, target_tokens=target_length
            )
            await self.progress_updater.update(progress=90, status="IN_PROGRESS")

        remaining_text = final_summary
        while remaining_text:
            chunk_size = random.randint(50, 200)
            chunk = remaining_text[:chunk_size]
            remaining_text = remaining_text[chunk_size:]

            await self.progress_updater.update(
                progress=95,  # Keep progress at 95% during chunked updates
                status="IN_PROGRESS",
                payload=SummaryProgressData(newText=chunk),
            )
            # Add a small delay to simulate processing time and avoid overwhelming the client
            await asyncio.sleep(0.1)

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

    async def map_reduce_summarize(
        self, document_id: str, db: TypedAsyncIOMotorDatabase
    ) -> Dict[str, str]:
        # Retrieve document from MongoDB
        obj_id = ObjectId(document_id)
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        document = await collection.find_one({"_id": obj_id})
        entire_text: str = document["extracted_text"]

        await self.progress_updater.update(progress=5, status="IN_PROGRESS")

        # Split text into chunks
        chunk_size = 4000  # Adjust based on your needs and model limits
        chunks = [
            entire_text[i : i + chunk_size]
            for i in range(0, len(entire_text), chunk_size)
        ]
        total_chunks = len(chunks)

        async def summarize_chunk(chunk: str, chunk_index: int) -> str:
            async with self.semaphore:
                messages: List[ChatCompletionMessageParam] = [
                    {
                        "role": "system",
                        "content": "You are an expert agent in information extraction and summarization",
                    },
                    {"role": "user", "content": chunk},
                ]
                summary = await self._make_api_call(
                    messages,
                    self.model_pair_config["chat_model"]["max_output_tokens"] // 2,
                )
                await self.progress_updater.update(
                    progress=5 + (60 * (chunk_index + 1) / total_chunks),
                    status="IN_PROGRESS",
                )
                return summary

        def final_summary_prompt(
            combined_summary: str, document: Dict[str, Any]
        ) -> str:
            header = "Read the following concatenation of summaries of chunks of text"
            if document["extracted_metadata"].get("title"):
                header += f" from {document['extracted_metadata']['title']}"
            if document["extracted_metadata"].get("creator"):
                header += f" by {document['extracted_metadata']['creator']}"

            metadata_string = ""
            for key, value in document["extracted_metadata"].items():
                metadata_string += f"{key}: {value}\n"

            if metadata_string:
                header += f". Additionally, consider this metadata text as appropriate: {metadata_string}"
            return f"""
                {header}:
                ---------------  
                {combined_summary}  
                ---------------  
                
                Your tasks are as follows:  
                1. Summarize the concatenation of summaries above into a single, intelligible summary.
                2. At the end of the summary, add key insights, conclusions, recommendations, or any other relevant information that you consider important.
                3. Structure the document in an intelligible, coherent and readable manner.

            """

        summarization_tasks: List[Coroutine[Any, Any, str]] = []
        for i, chunk in enumerate(chunks):
            prompt = f"""
            Read the following context document:  
            ---------------  
            {chunk}  
            ---------------  
            
            Your tasks are as follows:  
            1.- Write an extensive, fluid, and continuous paragraph summarizing the most important aspects of the information you have read.  
            2.- You can only synthesize your response using exclusively the information from the context document.  

            """
            summarization_tasks.append(summarize_chunk(prompt, i))

        chunk_summaries = await asyncio.gather(*summarization_tasks)

        await self.progress_updater.update(progress=65, status="IN_PROGRESS")

        # Reduce step: Combine chunk summaries
        combined_summary = "\n\n".join(chunk_summaries)
        combined_summary_prompt = final_summary_prompt(combined_summary, document)

        # Final summarization
        final_summary_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "You are a helpful assistant that creates comprehensive document summaries.",
            },
            {"role": "user", "content": combined_summary_prompt},
        ]

        final_summary = await self._make_api_call(
            final_summary_messages,
            self.model_pair_config["chat_model"]["max_output_tokens"],
        )

        await self.progress_updater.update(progress=90, status="IN_PROGRESS")

        # Chunked updates of the final summary
        remaining_text = final_summary
        while remaining_text:
            chunk_size = random.randint(50, 200)
            chunk = remaining_text[:chunk_size]
            remaining_text = remaining_text[chunk_size:]

            await self.progress_updater.update(
                progress=95,
                status="IN_PROGRESS",
                payload=SummaryProgressData(newText=chunk),
            )
            await asyncio.sleep(0.1)

        await self.progress_updater.complete(
            payload=SummaryProgressData(
                completeText=final_summary,
            )
        )

        return {"summary": final_summary}

    async def sequential_summarize(
        self, document_id: str, db: TypedAsyncIOMotorDatabase
    ) -> Dict[str, str]:
        # Retrieve document from MongoDB
        obj_id = ObjectId(document_id)
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        document = await collection.find_one({"_id": obj_id})
        entire_text: str = document["extracted_text"]

        await self.progress_updater.update(progress=5, status="IN_PROGRESS")

        # Split text into chunks
        chunk_size = 2000  # Smaller chunks for more frequent updates
        chunks = [
            entire_text[i : i + chunk_size]
            for i in range(0, len(entire_text), chunk_size)
        ]
        total_chunks = len(chunks)

        summary_so_far = ""
        final_summary = ""

        for i, chunk in enumerate(chunks):
            messages: List[ChatCompletionMessageParam] = [
                {
                    "role": "system",
                    "content": "You are summarizing a document in order. Maintain key information and context. Your summary should flow naturally from the previous part.",
                },
                {
                    "role": "user",
                    "content": f"Previous summary:\n{summary_so_far}\n\nNext part to summarize:\n{chunk}",
                },
            ]

            chunk_summary = await self._make_api_call(
                messages, self.model_pair_config["chat_model"]["max_output_tokens"] // 2
            )

            summary_so_far += chunk_summary + " "
            final_summary = summary_so_far

            # Update progress
            progress = 5 + (85 * (i + 1) / total_chunks)
            await self.progress_updater.update(
                progress=progress,
                status="IN_PROGRESS",
                payload=SummaryProgressData(newText=chunk_summary),
            )

        # Final touch-up
        final_messages: List[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "Review and refine the following document summary. Ensure it's coherent, well-structured, and captures the main points of the entire document.",
            },
            {"role": "user", "content": final_summary},
        ]

        final_summary = await self._make_api_call(
            final_messages, self.model_pair_config["chat_model"]["max_output_tokens"]
        )

        await self.progress_updater.complete(
            payload=SummaryProgressData(
                completeText=final_summary,
            )
        )

        return {"summary": final_summary}
