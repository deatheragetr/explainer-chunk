from fastapi import APIRouter, HTTPException, Body
from db.models.document_uploads import MongoDocumentUpload, MongoFileDetails
from api.requests.document_upload import DocumentUploadRequest
from api.responses.document_upload import DocumentUploadResponse
from typing import Annotated
from config.environment import WasabiSettings
from config.mongo import db
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult

wasabiSettings = WasabiSettings()

router = APIRouter()

@router.post("/document-uploads/", response_model=DocumentUploadResponse)
async def upload_file(reqBody: Annotated[DocumentUploadRequest, Body()]):
    # register file with Wasabi
    try: 
        s3_url = f"{wasabiSettings.wasabi_endpoint_url}/{wasabiSettings.wasabi_document_bucket}/{reqBody.file_key}"

        # TODO Verify s3_url is valid before proceeding

        # Save to MongoDB
        document = MongoDocumentUpload(
            file_details=MongoFileDetails(
                file_name=reqBody.file_name,
                file_type=reqBody.file_type,
                file_key=reqBody.file_key,
                s3_url=s3_url
            )
        )

        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        result: InsertOneResult = await collection.insert_one(document)

        return DocumentUploadResponse(
            id=str(result.inserted_id),
            file_name=document["file_details"]["file_name"],
            file_type=document["file_details"]["file_type"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
