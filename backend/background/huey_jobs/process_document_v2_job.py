import asyncio
from bson import ObjectId
from typing import List, Dict, Any, Optional, cast
import os
import tempfile
from datetime import datetime, UTC

from config.huey import huey
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from db.models.document_uploads import MongoDocumentUpload, find_assistant_by_model
from config.environment import OpenAISettings
from config.logger import get_logger

# Correct import for Docling chunker
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

# Correct import for Elasticsearch
from elasticsearch import AsyncElasticsearch
from config.elasticsearch import ElasticsearchSettings

# Import OpenAI for embeddings
from openai import AsyncOpenAI

logger = get_logger()
openai_settings = OpenAISettings()
es_settings = ElasticsearchSettings()


class DoclingDocumentProcessor:
    def __init__(
        self,
        db: TypedAsyncIOMotorDatabase,
        es_client: AsyncElasticsearch,
    ):
        self.db = db
        self.es_client = es_client
        self.converter = DocumentConverter()
        # Create a chunker using the HybridChunker class
        self.chunker = HybridChunker(
            granularity="paragraph",  # Can be "section", "paragraph", "sentence"
            add_metadata=True,  # Include metadata for each chunk
        )

    async def get_document_upload(self, document_id: str) -> MongoDocumentUpload:
        """Retrieve document from MongoDB."""
        document = await self.db.document_uploads.find_one(
            {"_id": ObjectId(document_id)}
        )
        if not document:
            raise ValueError(f"Document with ID {document_id} not found")
        return document

    async def get_file_content(self, document: MongoDocumentUpload) -> str:
        """Create a temporary file to process with Docling."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file_path = temp_file.name
            # Download file from S3
            s3_bucket = document["file_details"]["s3_bucket"]
            s3_key = document["file_details"]["file_key"]
            from config.s3 import s3_client

            s3_client.download_file(s3_bucket, s3_key, temp_file_path)

            return temp_file_path

    async def process_document(self, document_id: str) -> Dict[str, Any]:
        """Process document with Docling and store in MongoDB and Elasticsearch."""
        try:
            # Get document from MongoDB
            document = await self.get_document_upload(document_id)

            # Get file path for Docling processing
            file_path = await self.get_file_content(document)

            logger.info(f"Processing document {document_id} with Docling")

            # Convert document using Docling
            conversion_result = self.converter.convert(file_path)
            docling_doc = conversion_result.document

            # Extract structured data from the document
            structured_data = self._extract_structured_data(docling_doc)

            # Create chunks using the Docling chunker
            chunks = self._create_chunks(docling_doc, document_id)

            # Store the processed data in MongoDB
            await self._update_mongodb(document_id, structured_data)

            # Store the chunks in Elasticsearch
            await self._store_in_elasticsearch(document_id, chunks)

            # Clean up temp file
            os.unlink(file_path)

            logger.info(f"Successfully processed document {document_id} with Docling")

            return {
                "document_id": document_id,
                "status": "success",
                "chunks_created": len(chunks),
                "structured_data": structured_data,
            }

        except Exception as e:
            logger.error(
                f"Error processing document {document_id} with Docling: {str(e)}"
            )
            raise

    def _extract_structured_data(self, docling_doc) -> Dict[str, Any]:
        """Extract structured data from Docling document."""
        # Get document metadata
        metadata = docling_doc.metadata

        # Extract title, authors, abstract if available
        title = docling_doc.title or "Untitled Document"

        # Get all headings in the document
        headings = []
        for heading in docling_doc.headings:
            headings.append(heading.text)

        # Extract tables if present
        tables = []
        for table in docling_doc.tables:
            tables.append(
                {
                    "caption": table.caption,
                    "rows": len(table.rows) if hasattr(table, "rows") else 0,
                    "cols": len(table.columns) if hasattr(table, "columns") else 0,
                }
            )

        # Extract figures if present
        figures = []
        for figure in docling_doc.figures:
            figures.append(
                {
                    "caption": figure.caption if hasattr(figure, "caption") else "",
                }
            )

        # Combine into structured data
        structured_data = {
            "title": title,
            "headings": headings,
            "tables_count": len(tables),
            "tables": tables,
            "figures_count": len(figures),
            "figures": figures,
            "metadata": metadata,
            "processed_at": datetime.now(UTC).isoformat(),
        }

        return structured_data

    def _create_chunks(self, docling_doc, document_id: str) -> List[Dict[str, Any]]:
        """Create chunks from Docling document using the HybridChunker."""
        chunks = []

        # Use the Docling chunker to create chunks
        doc_chunks = self.chunker.chunk(docling_doc)

        for i, chunk in enumerate(doc_chunks):
            # Get chunk text using the serialize method of the chunker
            text = self.chunker.serialize(chunk)

            # Get metadata properties if available
            metadata = {}
            if hasattr(chunk, "metadata"):
                metadata = chunk.metadata

            # Extract headings path if available
            heading_path = []
            if hasattr(chunk, "heading_path"):
                heading_path = chunk.heading_path
            elif "headings" in metadata:
                heading_path = metadata["headings"]

            # Get page number if available
            page_number = None
            if hasattr(chunk, "page_no"):
                page_number = chunk.page_no
            elif "page_no" in metadata:
                page_number = metadata["page_no"]

            # Create chunk data
            chunk_data = {
                "chunk_id": f"{document_id}_chunk_{i}",
                "document_id": document_id,
                "text": text,
                "heading_path": heading_path,
                "chunk_index": i,
                "chunk_type": chunk.label if hasattr(chunk, "label") else "text",
                "page_number": page_number,
                "section_path": "/".join(heading_path) if heading_path else "",
                "position_in_document": i
                / len(doc_chunks),  # Normalize position to 0-1
                "metadata": metadata,
            }

            chunks.append(chunk_data)

        return chunks

    async def _update_mongodb(
        self, document_id: str, structured_data: Dict[str, Any]
    ) -> None:
        """Update MongoDB with structured data from Docling."""
        # Update document in MongoDB with structured data
        await self.db.document_uploads.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "docling_structured_data": structured_data,
                    "docling_processed_at": datetime.now(UTC),
                }
            },
        )

    async def _store_in_elasticsearch(
        self, document_id: str, chunks: List[Dict[str, Any]]
    ) -> None:
        """Store document chunks in Elasticsearch with vector embeddings."""
        # First, check if the index exists, create it if it doesn't
        index_name = f"{es_settings.elasticsearch_index_prefix}academic_papers"

        if not await self.es_client.indices.exists(index=index_name):
            # Create index with mapping for dense vectors
            await self._create_elasticsearch_index(index_name)

        # Batch insert chunks into Elasticsearch
        actions = []

        # Generate embeddings for all chunks
        chunk_texts = [chunk["text"] for chunk in chunks]

        # Use OpenAI for embeddings (could replace with any embedding model)
        client = AsyncOpenAI(api_key=openai_settings.openai_api_key)

        # Process in batches of 100 to avoid rate limits
        batch_size = 100
        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i : i + batch_size]
            response = await client.embeddings.create(
                model="text-embedding-3-small", input=batch
            )

            # Add embeddings to chunks
            for j, embedding in enumerate(response.data):
                idx = i + j
                if idx < len(chunks):
                    # Create Elasticsearch document
                    es_doc = {
                        **chunks[idx],
                        "vector": embedding.embedding,
                    }

                    # Add to batch actions
                    actions.append(
                        {
                            "_index": index_name,
                            "_id": chunks[idx]["chunk_id"],
                            "_source": es_doc,
                        }
                    )

        # Bulk insert into Elasticsearch
        from elasticsearch.helpers import async_bulk

        await async_bulk(self.es_client, actions)

        logger.info(
            f"Stored {len(chunks)} chunks in Elasticsearch for document {document_id}"
        )

    async def _create_elasticsearch_index(self, index_name: str) -> None:
        """Create Elasticsearch index with appropriate mappings for academic papers."""
        # Define mapping with dense vector field for embeddings
        mapping = {
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "text": {"type": "text"},
                    "heading_path": {"type": "keyword"},
                    "chunk_index": {"type": "integer"},
                    "chunk_type": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "section_path": {"type": "text"},
                    "position_in_document": {"type": "float"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": 1536,  # Dimension for text-embedding-3-small
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
            "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1}},
        }

        await self.es_client.indices.create(index=index_name, body=mapping)
        logger.info(f"Created Elasticsearch index: {index_name}")


async def async_process_document_with_docling(document_id: str):
    """Asynchronous function to process document with Docling."""
    # Set up MongoDB connection
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def get_mongo_db():
        mongo_manager = MongoManager[TypedAsyncIOMotorDatabase](mongo_settings)
        await mongo_manager.connect()
        assert mongo_manager.db is not None
        try:
            yield mongo_manager.db
        finally:
            await mongo_manager.close()

    # Set up Elasticsearch connection
    @asynccontextmanager
    async def get_elasticsearch_client():
        es_client = AsyncElasticsearch(
            es_settings.elasticsearch_url,
            basic_auth=(
                es_settings.elasticsearch_user,
                es_settings.elasticsearch_password,
            ),
            verify_certs=es_settings.elasticsearch_verify_certs,
        )
        try:
            yield es_client
        finally:
            await es_client.close()

    # Process document
    async with get_mongo_db() as db, get_elasticsearch_client() as es_client:
        processor = DoclingDocumentProcessor(db, es_client)
        return await processor.process_document(document_id)


@huey.task()
def process_document_with_docling(document_id: str):
    """Huey task to process document with Docling."""
    logger.info(f"Starting Docling processing for document_id={document_id}")
    try:
        # Run async function with asyncio
        result = asyncio.run(async_process_document_with_docling(document_id))
        logger.info(f"Finished Docling processing for document_id={document_id}")
        return result
    except Exception as e:
        logger.exception(
            f"Error in Docling processing for document_id={document_id}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
