from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase
from config.environment import MongoSettings
from db.models.document_uploads import MongoDocumentUpload

class TypedAsyncIOMotorDatabase(AsyncIOMotorDatabase):
    # List the collections in the database here
    document_uploads: AsyncIOMotorCollection[MongoDocumentUpload]

mongo_settings: MongoSettings = MongoSettings()
# MongoDB connection
client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_settings.mongo_url) # type: ignore
db: TypedAsyncIOMotorDatabase = client[mongo_settings.mongo_db] # type: ignore
