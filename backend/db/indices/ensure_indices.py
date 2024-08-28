import asyncio
from typing import Any, List, Coroutine
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from config.mongo import (
    TypedAsyncIOMotorDatabase,
    AsyncIOMotorCollection,
    mongo_manager,
)
from config.logger import get_logger

logger = get_logger()


async def create_index_with_logging(
    collection: AsyncIOMotorCollection[Any], index_model: IndexModel
) -> None:
    try:
        index_name = await collection.create_indexes([index_model])
        logger.info(
            f"Successfully created index '{index_name}' on collection '{collection.name}'"
        )
    except PyMongoError as e:
        logger.error(
            f"Failed to create index on collection '{collection.name}': {str(e)}"
        )
        logger.error(f"Index definition: {index_model.document}")
        raise


async def ensure_indices(db: TypedAsyncIOMotorDatabase):
    indices = [
        # Chats collection indices
        IndexModel(
            [
                ("document_upload_id", ASCENDING),
                ("model_name", ASCENDING),
                ("messages.created_at", DESCENDING),
            ],
            background=True,
            name="chats_document_model_message_date",
        ),
        # Add more indices for other collections as needed
    ]

    tasks: List[Coroutine[Any, Any, None]] = []
    for index in indices:
        tasks.append(create_index_with_logging(db.chats, index))

    # Add more collections here as needed
    # e.g., tasks.append(create_index_with_logging(db.another_collection, another_index))

    try:
        await asyncio.gather(*tasks)
        logger.info("All MongoDB indices ensured successfully")
    except PyMongoError:
        logger.error(
            "Failed to ensure all MongoDB indices. Some indices may not have been created."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred while ensuring indices: {str(e)}")


async def ensure_indices_with_manager():
    async with mongo_manager.get_database() as db:
        await ensure_indices(db)


if __name__ == "__main__":
    # This allows you to run this script directly to ensure indices if needed
    async def main():
        await mongo_manager.connect()
        try:
            await ensure_indices_with_manager()
        finally:
            await mongo_manager.close()

    asyncio.run(main())
