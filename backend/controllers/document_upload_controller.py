from fastapi import APIRouter, HTTPException, Body
from bson import ObjectId
from db.models.document_uploads import MongoDocumentUpload, MongoFileDetails
from api.requests.document_upload import DocumentUploadRequest
from api.responses.document_upload import (
    DocumentUploadResponse,
    DocumentRetrieveResponse,
)
from api.utils.s3_utils import verify_s3_object
from api.utils.url_friendly import make_url_friendly
from typing import Annotated
from config.environment import WasabiSettings
from config.mongo import db
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from pymongo.errors import DuplicateKeyError
from config.s3 import s3_client

wasabiSettings = WasabiSettings()
router = APIRouter()


@router.post("/document-uploads/", response_model=DocumentUploadResponse)
async def upload_document(reqBody: Annotated[DocumentUploadRequest, Body()]):
    # register file with Wasabi
    try:
        s3_url = f"{wasabiSettings.wasabi_endpoint_url}/{wasabiSettings.wasabi_document_bucket}/{reqBody.file_key}"
        doc_id = reqBody.extracted_object_id

        # Verify s3_url is valid
        if not await verify_s3_object(
            s3_client, wasabiSettings.wasabi_document_bucket, reqBody.file_key
        ):
            raise HTTPException(status_code=404, detail="File not found")

        # Save to MongoDB
        document = MongoDocumentUpload(
            _id=doc_id,
            file_details=MongoFileDetails(
                file_name=reqBody.file_name,
                file_type=reqBody.file_type,
                file_key=reqBody.file_key,
                s3_bucket=wasabiSettings.wasabi_document_bucket,
                url_friendly_file_name=make_url_friendly(reqBody.file_name),
                s3_url=s3_url,
            ),
        )

        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        try:
            result: InsertOneResult = await collection.insert_one(document)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409, detail="Document with this ID already exists"
            )

        return DocumentUploadResponse(
            id=str(result.inserted_id),
            file_name=document["file_details"]["file_name"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            file_type=document["file_details"]["file_type"],
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/document-uploads/{document_id}", response_model=DocumentRetrieveResponse)
async def get_document(document_id: str):
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(document_id)

        # Retrieve document from MongoDB
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        document = await collection.find_one({"_id": obj_id})

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Generate pre-signed URL
        try:
            presigned_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": document["file_details"]["s3_bucket"],
                    "Key": document["file_details"]["file_key"],
                },
                ExpiresIn=3600,
            )  # URL expires in 1 hour
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating pre-signed URL: {str(e)}"
            )

        return DocumentRetrieveResponse(
            id=str(document["_id"]),
            file_name=document["file_details"]["file_name"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            file_type=document["file_details"]["file_type"],
            presigned_url=presigned_url,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))