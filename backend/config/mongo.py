from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from config.environment import MongoSettings
from db.models.document_uploads import MongoDocumentUpload

from typing import Optional, TypeVar, Generic, Dict, Any, AsyncIterator

from contextlib import asynccontextmanager
from pymongo.server_api import ServerApi


DocType = TypeVar('DocType', bound=Dict[str, Any])

class TypedAsyncIOMotorDatabase(AsyncIOMotorDatabase):
    # List the collections in the database here
    document_uploads: AsyncIOMotorCollection[MongoDocumentUpload]

# mongo_settings: MongoSettings = MongoSettings()
# # MongoDB connection
# client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_settings.mongo_url) # type: ignore
# db: TypedAsyncIOMotorDatabase = client[mongo_settings.mongo_db] # type: ignore

# Define a type variable for the database
DBType = TypeVar('DBType', bound=TypedAsyncIOMotorDatabase)


class MongoManager(Generic[DBType]):
    def __init__(self, settings: MongoSettings):
        self.settings = settings
        self.client: Optional[AsyncIOMotorClient[DBType]] = None
        self.db: Optional[TypedAsyncIOMotorDatabase] = None

    async def connect(self):
        if self.client is None:
            try:
                self.client = AsyncIOMotorClient(
                    self.settings.mongo_url,
                    serverSelectionTimeoutMS=5000,
                    maxPoolSize=self.settings.max_pool_size,
                    minPoolSize=self.settings.min_pool_size,
                    server_api=ServerApi('1')
                )
                await self.client.server_info()  # Trigger connection to verify it's successful
                self.db = self.client[self.settings.mongo_db]
                print("Connected to MongoDB")
            except Exception as e:
                print(f"Failed to connect to MongoDB: {e}")
                raise

    async def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            print("Closed MongoDB connection")

    @asynccontextmanager
    async def get_database(self) -> AsyncIterator[TypedAsyncIOMotorDatabase]:
        if self.db is None:
            await self.connect()
        assert self.db is not None
        try:
            yield self.db
        finally:
            pass  # We're not closing the connection here, as it's managed by the pool

mongo_settings = MongoSettings()
mongo_manager = MongoManager(mongo_settings)

async def get_db() -> AsyncIterator[TypedAsyncIOMotorDatabase]:
    async with mongo_manager.get_database() as db:
        yield db
