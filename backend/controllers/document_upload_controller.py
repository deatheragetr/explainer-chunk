from fastapi import APIRouter, HTTPException, Body, Depends
from bson import ObjectId
from db.models.document_uploads import (
    MongoDocumentUpload,
    create_mongo_file_details,
    generate_s3_url,
    AllowedS3Buckets,
    SourceType,
)
from api.requests.document_upload import DocumentUploadRequest
from api.responses.document_upload import (
    DocumentUploadResponse,
    DocumentRetrieveResponse,
    DocumentUploadImportExternalResponse,
)
from api.utils.s3_utils import verify_s3_object
from typing import Annotated
from config.environment import S3Settings
from config.mongo import get_db, TypedAsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from pymongo.errors import DuplicateKeyError
from config.s3 import s3_client
from background.huey_jobs.process_document_job import process_document

s3_settings = S3Settings()
router = APIRouter()


@router.post(
    "/document-uploads/imports", response_model=DocumentUploadImportExternalResponse
)
async def upload_document_from_import():
    try:
        # TODO: Push to redis websocket list along with user data
        return DocumentUploadImportExternalResponse(id=str(ObjectId()))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/document-uploads/",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    reqBody: Annotated[DocumentUploadRequest, Body()],
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
):
    # register file with S3 and save to MongoDB
    try:
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        s3_url = generate_s3_url(
            s3_settings.s3_host,
            AllowedS3Buckets.DOCUMENT_UPLOADS,
            reqBody.file_key,
        )
        doc_id = reqBody.extracted_object_id

        # Verify s3_url is valid
        if not await verify_s3_object(
            s3_client, s3_settings.s3_document_bucket, reqBody.file_key
        ):
            raise HTTPException(status_code=404, detail="File not found")

        # Save to MongoDB
        document = MongoDocumentUpload(
            _id=doc_id,
            file_details=create_mongo_file_details(
                file_name=reqBody.file_name,
                file_type=reqBody.file_type,
                file_key=reqBody.file_key,
                s3_bucket=s3_settings.s3_document_bucket,
                source=SourceType.FILE_UPLOAD,
                s3_url=s3_url,
            ),
            extracted_text=reqBody.extracted_text,
            extracted_metadata=reqBody.extracted_metadata,
            openai_assistants=[],
        )

        # Kick of background job to process document
        process_document(document_id=str(doc_id))

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
async def get_document(
    document_id: str, db: TypedAsyncIOMotorDatabase = Depends(get_db)
):
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(document_id)

        # Retrieve document from MongoDB
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        # Avoid fetching the entire document, with the potentially long extracted text
        document = await collection.find_one(
            {"_id": obj_id}, {"_id": 1, "file_details": 1}
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        try:
            if (
                document["file_details"]["s3_bucket"]
                == AllowedS3Buckets.PUBLIC_BUCKET.value
            ):
                # Web captures are public, so no need to generate pre-signed URL
                presigned_url = document["file_details"]["s3_url"]
            else:
                # Generate pre-signed URL
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
