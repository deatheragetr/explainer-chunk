import asyncio
from bson import ObjectId
from typing import List, Dict, Any, Optional, cast
import os
import tempfile
from datetime import datetime, UTC
import json

from config.huey import huey
from config.mongo import MongoManager, mongo_settings, TypedAsyncIOMotorDatabase
from db.models.document_uploads import MongoDocumentUpload, find_assistant_by_model
from config.environment import OpenAISettings
from config.logger import get_logger

# Correct import for Docling chunker
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

# Correct import for Elasticsearch
from elasticsearch import AsyncElasticsearch
from config.environment import ElasticsearchSettings

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
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_cls=StandardPdfPipeline,
                    backend=PyPdfiumDocumentBackend,
                ),
            },
        )
        # Create a chunker using the HybridChunker class
        # The token length warning is a "false alarm" according to Docling docs
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

            for item, level in docling_doc.iterate_items():
                print(f"Item type: {type(item)}, Level: {level}")

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
        """Extract structured data from Docling document including document outline."""
        # Initialize with safe defaults
        structured_data = {
            "title": "Untitled Document",
            "num_pages": 0,
            "headings": [],
            "tables_count": 0,
            "tables": [],
            "figures_count": 0,
            "figures": [],
            "document_metadata": {},
            "outline": [],  # New field for document outline/skeleton
            "processed_at": datetime.now(UTC).isoformat(),
        }

        # Extract document metadata
        if hasattr(docling_doc, "origin"):
            try:
                metadata = {}
                if hasattr(docling_doc.origin, "model_dump"):
                    metadata = docling_doc.origin.model_dump()
                elif hasattr(docling_doc.origin, "dict"):
                    metadata = docling_doc.origin.dict()
                else:
                    # Extract individual attributes
                    for attr in ["mimetype", "binary_hash", "filename", "uri"]:
                        if hasattr(docling_doc.origin, attr):
                            metadata[attr] = getattr(docling_doc.origin, attr)
                            if attr == "binary_hash" and metadata[attr] is not None:
                                metadata[attr] = str(metadata[attr])
                structured_data["document_metadata"] = metadata
            except Exception as e:
                print(f"Error extracting metadata: {str(e)}")

        # Get document title
        if hasattr(docling_doc, "name") and docling_doc.name:
            structured_data["title"] = docling_doc.name

        # Get number of pages
        if hasattr(docling_doc, "num_pages"):
            try:
                # Check if it's a method or an attribute
                if callable(docling_doc.num_pages):
                    structured_data["num_pages"] = docling_doc.num_pages()
                else:
                    structured_data["num_pages"] = docling_doc.num_pages
            except Exception as e:
                print(f"Error getting page count: {str(e)}")

        # Extract document outline/skeleton
        outline = self._extract_document_outline(docling_doc)
        structured_data["outline"] = outline

        # Extract headings from the outline for backward compatibility
        structured_data["headings"] = [
            item["text"]
            for item in outline
            if item["type"] in ["title", "section_header"]
        ]

        # Extract table data
        if hasattr(docling_doc, "tables"):
            try:
                tables = list(docling_doc.tables)
                structured_data["tables_count"] = len(tables)

                for table in tables:
                    table_info = {"caption": "", "rows": 0, "cols": 0, "data": []}

                    # Get caption_text
                    if hasattr(table, "caption_text") and callable(table.caption_text):
                        try:
                            table_info["caption"] = table.caption_text(docling_doc)
                        except Exception:
                            if hasattr(table, "captions") and table.captions:
                                # Try to get first caption
                                table_info["caption"] = "Table Caption"

                    # Try to get table data
                    if hasattr(table, "data") and table.data:
                        try:
                            if hasattr(table.data, "__iter__"):
                                table_data = []
                                for row_idx, row in enumerate(table.data):
                                    if hasattr(row, "__iter__"):
                                        row_data = []
                                        for col_idx, cell in enumerate(row):
                                            cell_text = (
                                                str(cell) if cell is not None else ""
                                            )
                                            row_data.append(cell_text)
                                        table_data.append(row_data)

                                if table_data:
                                    table_info["data"] = table_data
                                    table_info["rows"] = len(table_data)
                                    table_info["cols"] = (
                                        max(len(row) for row in table_data)
                                        if table_data
                                        else 0
                                    )
                        except Exception as e:
                            print(f"Error extracting table data: {str(e)}")

                    structured_data["tables"].append(table_info)
            except Exception as e:
                print(f"Error processing tables: {str(e)}")

        # Extract figure data
        if hasattr(docling_doc, "pictures"):
            try:
                figures = list(docling_doc.pictures)
                structured_data["figures_count"] = len(figures)

                for figure in figures:
                    figure_info = {"caption": "", "image_info": {}}

                    # Get caption_text
                    if hasattr(figure, "caption_text") and callable(
                        figure.caption_text
                    ):
                        try:
                            figure_info["caption"] = figure.caption_text(docling_doc)
                        except Exception:
                            if hasattr(figure, "captions") and figure.captions:
                                # Try to get first caption
                                figure_info["caption"] = "Figure Caption"

                    # Try to get image details
                    if hasattr(figure, "image") and figure.image:
                        try:
                            if hasattr(figure.image, "width") and hasattr(
                                figure.image, "height"
                            ):
                                figure_info["image_info"]["width"] = figure.image.width
                                figure_info["image_info"][
                                    "height"
                                ] = figure.image.height

                            # Try to get other potentially useful image properties
                            for attr in ["format", "page", "dpi"]:
                                if hasattr(figure.image, attr):
                                    value = getattr(figure.image, attr)
                                    if value is not None:
                                        figure_info["image_info"][attr] = value
                        except Exception as e:
                            print(f"Error extracting image details: {str(e)}")

                    structured_data["figures"].append(figure_info)
            except Exception as e:
                print(f"Error processing figures: {str(e)}")

        return structured_data

    def _extract_document_outline(self, docling_doc) -> List[Dict[str, Any]]:
        """
        Extract document outline/skeleton from Docling document.

        Creates a hierarchical representation of the document structure,
        including title, sections, subsections, and their page numbers.
        """
        outline = []
        current_section_stack = []  # Track section nesting using a stack
        item_counter = 0  # Global counter for unique IDs

        # First pass: collect all section headers and their levels
        for item, level in docling_doc.iterate_items():
            item_type = type(item).__name__

            # Extract page number from item's provenance if available
            page_number = None
            if hasattr(item, "prov") and item.prov:
                for prov in item.prov:
                    if hasattr(prov, "page_no"):
                        page_number = prov.page_no
                        break

            # Process title and section headers for the outline
            if (
                item_type == "TitleItem"
                or hasattr(item, "label")
                and item.label == "title"
            ):
                outline_item = {
                    "id": f"outline_item_{item_counter}",  # Use global counter
                    "type": "title",
                    "text": item.text if hasattr(item, "text") else "Untitled",
                    "level": 0,  # Title is always top level
                    "page_number": page_number or 1,  # Default to page 1 if not found
                    "parent_id": None,  # Titles are top-level
                }
                item_counter += 1
                outline.append(outline_item)

            elif item_type == "SectionHeaderItem" or (
                hasattr(item, "label") and item.label == "section_header"
            ):
                # Get section level (defaults to 1 if not available)
                section_level = (
                    getattr(item, "level", 1) if hasattr(item, "level") else 1
                )

                outline_item = {
                    "id": f"outline_item_{item_counter}",  # Use global counter
                    "type": "section_header",
                    "text": item.text if hasattr(item, "text") else "Untitled Section",
                    "level": section_level,
                    "page_number": page_number or 1,  # Default to page 1 if not found
                    "parent_id": None,  # Will be set below if there's a parent
                }
                item_counter += 1

                # Update the section stack based on the current section's level
                while (
                    current_section_stack
                    and current_section_stack[-1]["level"] >= section_level
                ):
                    current_section_stack.pop()

                # Set parent_id if we have a parent section
                if current_section_stack:
                    outline_item["parent_id"] = current_section_stack[-1]["id"]

                # Add to outline and update the stack
                outline.append(outline_item)
                current_section_stack.append(outline_item)

            # Optionally track other significant elements like tables and figures
            elif item_type == "TableItem" or (
                hasattr(item, "label") and item.label == "table"
            ):
                caption = (
                    item.caption_text(docling_doc)
                    if hasattr(item, "caption_text") and callable(item.caption_text)
                    else ""
                )

                table_item = {
                    "id": f"outline_item_{item_counter}",  # Use global counter
                    "type": "table",
                    "text": f"Table: {caption}",
                    "page_number": page_number or 1,  # Default to page 1 if not found
                    "parent_id": (
                        current_section_stack[-1]["id"]
                        if current_section_stack
                        else None
                    ),
                }
                item_counter += 1
                outline.append(table_item)

            elif item_type == "PictureItem" or (
                hasattr(item, "label") and item.label == "picture"
            ):
                caption = (
                    item.caption_text(docling_doc)
                    if hasattr(item, "caption_text") and callable(item.caption_text)
                    else ""
                )

                figure_item = {
                    "id": f"outline_item_{item_counter}",  # Use global counter
                    "type": "figure",
                    "text": f"Figure: {caption}",
                    "page_number": page_number or 1,  # Default to page 1 if not found
                    "parent_id": (
                        current_section_stack[-1]["id"]
                        if current_section_stack
                        else None
                    ),
                }
                item_counter += 1
                outline.append(figure_item)

        # Return the flat outline with explicit parent-child relationships
        return outline

    def _flatten_outline(self, nested_outline, parent_id=None, result=None):
        """
        Convert a nested outline to a flat list with parent/child relationships.
        This format may be easier to work with in some applications.
        """
        if result is None:
            result = []

        for item in nested_outline:
            # Create a copy without the children
            flat_item = {k: v for k, v in item.items() if k != "children"}
            flat_item["parent_id"] = parent_id

            result.append(flat_item)

            # Process children recursively
            if "children" in item and item["children"]:
                self._flatten_outline(item["children"], item["id"], result)

        return result

    def _create_chunks(self, docling_doc, document_id: str) -> List[Dict[str, Any]]:
        """Create chunks from Docling document using the HybridChunker."""
        chunks = []

        # Get chunks from the document using the Docling chunker
        doc_chunks = list(self.chunker.chunk(docling_doc))

        # Process each chunk
        for i, chunk in enumerate(doc_chunks):
            # Get chunk text using the serialize method of the chunker
            text = self.chunker.serialize(chunk)

            # Extract metadata
            metadata = {}
            if hasattr(chunk, "metadata") and chunk.metadata:
                # Convert metadata to a serializable format
                metadata = self._ensure_serializable(chunk.metadata)

            # Extract headings path if available in chunk
            heading_path = []
            if hasattr(chunk, "heading_path"):
                heading_path = chunk.heading_path
            elif (
                hasattr(chunk, "metadata")
                and chunk.metadata
                and "headings" in chunk.metadata
            ):
                heading_path = chunk.metadata["headings"]

            # Extract page number if available
            page_number = None
            if hasattr(chunk, "page_no"):
                page_number = chunk.page_no
            elif (
                hasattr(chunk, "metadata")
                and chunk.metadata
                and "page_no" in chunk.metadata
            ):
                page_number = chunk.metadata["page_no"]

            # Create chunk data
            chunk_data = {
                "chunk_id": f"{document_id}_chunk_{i}",
                "document_id": document_id,
                "text": text,
                "heading_path": heading_path if heading_path else [],
                "chunk_index": i,
                "chunk_type": (
                    getattr(chunk, "label", "text")
                    if hasattr(chunk, "label")
                    else "text"
                ),
                "page_number": page_number,
                "section_path": (
                    "/".join(str(h) for h in heading_path) if heading_path else ""
                ),
                "position_in_document": (
                    i / len(doc_chunks) if doc_chunks else 0
                ),  # Normalize position to 0-1
                "metadata": metadata,
            }

            chunks.append(chunk_data)

        return chunks

    def _ensure_serializable(self, obj):
        """Make sure objects are serializable for MongoDB and handle large integers."""
        if hasattr(obj, "model_dump"):
            # For Pydantic v2
            return self._ensure_serializable(obj.model_dump())
        elif hasattr(obj, "dict"):
            # For Pydantic v1
            return self._ensure_serializable(obj.dict())
        elif isinstance(obj, dict):
            return {k: self._ensure_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._ensure_serializable(item) for item in obj]
        elif isinstance(obj, (str, float, bool, type(None))):
            return obj
        elif isinstance(obj, int):
            # Handle large integers that exceed MongoDB's 8-byte limit
            try:
                # Check if the int fits within MongoDB's limits
                # Max 64-bit signed int: 9,223,372,036,854,775,807
                if obj > 9223372036854775807 or obj < -9223372036854775808:
                    # Convert to string if too large
                    return str(obj)
                return obj
            except OverflowError:
                # Handle any overflow errors by converting to string
                return str(obj)
        else:
            # For any other objects, convert to string representation
            return str(obj)

    async def _update_mongodb(
        self, document_id: str, structured_data: Dict[str, Any]
    ) -> None:
        """Update MongoDB with structured data from Docling."""
        # Ensure structured_data is serializable
        serializable_data = self._ensure_serializable(structured_data)

        # Update document in MongoDB with structured data
        await self.db.document_uploads.update_one(
            {"_id": ObjectId(document_id)},
            {
                "$set": {
                    "docling_structured_data": serializable_data,
                    "docling_processed_at": datetime.now(UTC),
                }
            },
        )

    async def _store_in_elasticsearch(
        self, document_id: str, chunks: List[Dict[str, Any]]
    ) -> None:
        """Store document chunks in Elasticsearch with vector embeddings and handle connection errors."""
        if not chunks:
            logger.warning(f"No chunks to store for document {document_id}")
            return

        # First, check if the index exists, create it if it doesn't
        index_name = f"{es_settings.elasticsearch_index_prefix}academic_papers"

        # Retry mechanism for index existence check
        max_retries = 3
        retry_count = 0
        index_exists = False

        while retry_count < max_retries:
            try:
                index_exists = await self.es_client.indices.exists(index=index_name)
                break
            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Elasticsearch connection error (attempt {retry_count}/{max_retries}): {str(e)}"
                )
                if retry_count >= max_retries:
                    logger.error(
                        f"Failed to connect to Elasticsearch after {max_retries} attempts"
                    )
                    raise
                # Exponential backoff before retry
                await asyncio.sleep(2**retry_count)

        # Create index if it doesn't exist
        if not index_exists:
            await self._create_elasticsearch_index(index_name)

        # Generate embeddings for all chunks
        chunk_texts = [chunk["text"] for chunk in chunks]

        # Use OpenAI for embeddings
        client = AsyncOpenAI(api_key=openai_settings.openai_api_key)

        # Process in batches to avoid rate limits
        batch_size = 100
        actions = []

        for i in range(0, len(chunk_texts), batch_size):
            batch = chunk_texts[i : i + batch_size]
            try:
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
            except Exception as e:
                logger.error(
                    f"Error generating embeddings for batch starting at index {i}: {str(e)}"
                )
                # Continue with other batches rather than failing completely
                continue

        if not actions:
            logger.warning(
                f"No valid actions to store in Elasticsearch for document {document_id}"
            )
            return

        # Bulk insert into Elasticsearch with retry logic
        from elasticsearch.helpers import async_bulk

        max_bulk_retries = 3
        bulk_retry_count = 0

        while bulk_retry_count < max_bulk_retries:
            try:
                # Use a reasonable timeout for bulk operations
                success, errors = await async_bulk(
                    self.es_client,
                    actions,
                    request_timeout=60,
                    raise_on_error=False,  # Don't raise an exception on document errors
                    stats_only=False,  # Return details about errors
                )

                if errors:
                    logger.warning(
                        f"Some chunks had errors during indexing: {len(errors)} errors"
                    )
                    for error in errors[:5]:  # Log first 5 errors
                        logger.warning(f"Indexing error: {str(error)}")

                logger.info(
                    f"Stored {success} chunks in Elasticsearch for document {document_id}"
                )
                break

            except Exception as e:
                bulk_retry_count += 1
                logger.warning(
                    f"Elasticsearch bulk indexing error (attempt {bulk_retry_count}/{max_bulk_retries}): {str(e)}"
                )
                if bulk_retry_count >= max_bulk_retries:
                    logger.error(
                        f"Failed to store chunks in Elasticsearch after {max_bulk_retries} attempts"
                    )
                    raise
                # Exponential backoff before retry
                await asyncio.sleep(2**bulk_retry_count)

    async def _create_elasticsearch_index(self, index_name: str) -> None:
        """Create Elasticsearch index with appropriate mappings for academic papers."""
        try:
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

            # Create index with proper error handling
            try:
                await self.es_client.indices.create(index=index_name, body=mapping)
                logger.info(f"Created Elasticsearch index: {index_name}")
            except Exception as e:
                # Check if it's already exists error which can be ignored
                if "resource_already_exists_exception" in str(e):
                    logger.info(f"Elasticsearch index {index_name} already exists")
                else:
                    logger.error(f"Error creating Elasticsearch index: {str(e)}")
                    raise

        except Exception as e:
            logger.error(f"Failed to create Elasticsearch index: {str(e)}")
            raise


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

    @asynccontextmanager
    async def get_elasticsearch_client():
        """Context manager to create and properly close an Elasticsearch client.
        Handles HTTPS connections with appropriate SSL configuration.
        """
        # Create client configuration based on settings
        hosts = [es_settings.elasticsearch_url]

        # Configure client based on settings
        client_kwargs = {
            "hosts": hosts,
            "basic_auth": (
                es_settings.elasticsearch_user,
                es_settings.elasticsearch_password,
            ),
            "verify_certs": es_settings.elasticsearch_verify_certs,
            "ssl_show_warn": True,  # Always show SSL warnings for debugging
        }

        # Add CA certificate path if provided
        if (
            hasattr(es_settings, "elasticsearch_ca_certs")
            and es_settings.elasticsearch_ca_certs
        ):
            client_kwargs["ca_certs"] = es_settings.elasticsearch_ca_certs

        # Create the client
        es_client = AsyncElasticsearch(**client_kwargs)

        try:
            # Test connection to ensure it works
            try:
                info = await es_client.info()
                logger.info(
                    f"Successfully connected to Elasticsearch: {info['version']['number']}"
                )
            except Exception as e:
                logger.warning(
                    f"Elasticsearch connection warning (will retry operations): {str(e)}"
                )

            yield es_client
        finally:
            await es_client.close()

    async with get_mongo_db() as db, get_elasticsearch_client() as es_client:
        processor = DoclingDocumentProcessor(db, es_client)
        return await processor.process_document(document_id)


@huey.task()
def process_document_with_docling(document_id: str):
    """Huey task to process document with Docling."""
    logger.info(f"Starting Docling processing for document_id={document_id}")
    try:
        # asyncio.run handles event loop creation and cleanup
        result = asyncio.run(async_process_document_with_docling(document_id))
        logger.info(f"Finished Docling processing for document_id={document_id}")
        return result
    except Exception as e:
        logger.exception(
            f"Error in Docling processing for document_id={document_id}: {str(e)}"
        )
        raise  # Re-raise the exception so Huey marks the task as failed
