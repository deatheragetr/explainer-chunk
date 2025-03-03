import traceback
from fastapi import APIRouter, HTTPException, Body, Depends, Query
from typing import Optional, List, Any, Union
from bson import ObjectId
from db.models.document_uploads import (
    MongoDocumentUpload,
    create_mongo_file_details,
    generate_s3_url,
    AllowedS3Buckets,
    SourceType,
    ThumbnailDetails,
    MongoFileDetails,
    Note,
    get_display_title,
)
from api.requests.document_upload import (
    DocumentUploadRequest,
    NoteRequest,
    DocumentUpdateRequest,
)
from api.responses.document_upload import (
    DocumentUploadResponse,
    DocumentRetrieveResponse,
    DocumentUploadImportExternalResponse,
    PaginatedDocumentUploadsResponse,
    ThumbnailInfo,
    DocumentRetrieveResponseForPage,
    NoteResponse,
)
from api.utils.s3_utils import verify_s3_object
from typing import Annotated
from config.environment import S3Settings
from config.mongo import get_db, TypedAsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo.results import InsertOneResult
from pymongo.errors import DuplicateKeyError
from config.s3 import s3_client, S3Client
from config.logger import get_logger
from background.huey_jobs.process_document_job import process_document
from api.utils.auth_helper import get_current_user
from db.models.user import MongoUser

logger = get_logger()

s3_settings = S3Settings()
router = APIRouter()


@router.post(
    "/document-uploads/imports", response_model=DocumentUploadImportExternalResponse
)
async def upload_document_from_import():
    try:
        # TODO: Push to redis websocket list along with user data
        return DocumentUploadImportExternalResponse(id=str(ObjectId()))
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating import: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while creating the import"
        )


# Helper function to convert Note to NoteResponse
def note_to_response(note: Optional[Note]) -> Optional[NoteResponse]:
    if note is None:
        return None
    return NoteResponse(content=note.get("content", ""))


@router.post(
    "/document-uploads/",
    response_model=DocumentUploadResponse,
)
async def upload_document(
    reqBody: Annotated[DocumentUploadRequest, Body()],
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
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
            user_id=ObjectId(current_user["_id"]),
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
            custom_title=None,
            openai_assistants=[],
            chats=[],
            thumbnail=None,
            note=None,
        )

        # Kick of background job to process document
        process_document(document_id=str(doc_id))

        try:
            result: InsertOneResult = await collection.insert_one(document)
        except DuplicateKeyError:
            raise HTTPException(
                status_code=409, detail="Document with this ID already exists"
            )

        display_title = get_display_title(document)

        return DocumentUploadResponse(
            id=str(result.inserted_id),
            file_name=document["file_details"]["file_name"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            file_type=document["file_details"]["file_type"],
            note=note_to_response(document.get("note")),
            custom_title=document.get("custom_title"),
            title=display_title,
        )
    except HTTPException as e:
        raise e
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while uploading the document"
        )


@router.get("/document-uploads/{document_id}", response_model=DocumentRetrieveResponse)
async def get_document(
    document_id: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    try:
        # Convert string to ObjectId
        obj_id = ObjectId(document_id)
        user_id = ObjectId(current_user["_id"])

        # Retrieve document from MongoDB
        collection: AsyncIOMotorCollection[MongoDocumentUpload] = db.document_uploads
        # Avoid fetching the entire document, with the potentially long extracted text
        document = await collection.find_one(
            {"_id": obj_id, "user_id": user_id},
            {"_id": 1, "file_details": 1, "custom_title": 1, "extracted_metadata": 1},
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
                presigned_url = generate_presigned_url(
                    document["file_details"], s3_client
                )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating pre-signed URL: {str(e)}"
            )

        display_title = get_display_title(document)

        return DocumentRetrieveResponse(
            id=str(document["_id"]),
            file_name=document["file_details"]["file_name"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            file_type=document["file_details"]["file_type"],
            presigned_url=presigned_url,
            note=note_to_response(document.get("note")),
            custom_title=document.get("custom_title"),
            title=display_title,
        )
    except HTTPException as e:
        raise e
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Error fetching document: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching the document"
        )


@router.get("/document-uploads", response_model=PaginatedDocumentUploadsResponse)
async def get_document_uploads(
    before: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Number of documents to return"),
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    try:
        collection = db.document_uploads
        user_id = ObjectId(current_user["_id"])

        # Construct query based on pagination
        if before:
            query = {"user_id": user_id, "_id": {"$lt": ObjectId(before)}}
        else:
            query = {"user_id": user_id}

        cursor = (
            collection.find(
                query,
                {
                    "_id": 1,
                    "file_details": 1,
                    "thumbnail": 1,
                    "extracted_metadata": 1,
                    "custom_title": 1,
                },
            )
            .sort("_id", -1)
            .limit(limit + 1)
        )  # Fetch one extra to determine if there are more results

        documents: List[Any] = await cursor.to_list(length=limit + 1)  # type: ignore

        next_cursor = None
        if len(documents) > limit:
            next_cursor = str(documents[-1]["_id"])
            documents = documents[:limit]

        response_documents: List[DocumentRetrieveResponseForPage] = []
        for doc in documents:
            presigned_url = generate_presigned_url(doc.get("thumbnail", {}), s3_client)
            display_title = get_display_title(doc)

            response_doc = DocumentRetrieveResponseForPage(
                id=str(doc["_id"]),
                file_name=doc["file_details"]["file_name"],
                file_type=doc["file_details"]["file_type"],
                url_friendly_file_name=doc["file_details"]["url_friendly_file_name"],
                thumbnail=ThumbnailInfo(presigned_url=presigned_url),
                extracted_metadata=doc.get("extracted_metadata"),
                note=note_to_response(doc.get("note")),
                custom_title=doc.get("custom_title"),
                title=display_title,
            )
            response_documents.append(response_doc)

        return PaginatedDocumentUploadsResponse(
            documents=response_documents, next_cursor=next_cursor
        )
    except HTTPException as e:
        raise e
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid document ID or pagination parameter"
        )
    except Exception as e:
        logger.error(f"Error in get_document_uploads: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, detail="An error occurred while fetching documents"
        )


def generate_presigned_url(
    file_details: Union[MongoFileDetails, ThumbnailDetails, None], s3_client: S3Client
) -> str:
    # conditional checks because file/thumbnail details are generated in the background and may not
    # yet be present when this function is called
    if file_details is None:
        return ""
    if "s3_bucket" not in file_details or "file_key" not in file_details:
        return ""
    try:
        if file_details["s3_bucket"] == AllowedS3Buckets.PUBLIC_BUCKET.value:
            return file_details["s3_url"]
        else:
            return s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": file_details["s3_bucket"],
                    "Key": file_details["file_key"],
                },
                ExpiresIn=3600,
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating pre-signed URL: {str(e)}"
        )


@router.put("/document-uploads/{document_upload_id}/note", response_model=NoteResponse)
async def save_note(
    document_upload_id: str,
    content: NoteRequest,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    try:
        obj_id = ObjectId(document_upload_id)
        user_id = ObjectId(current_user["_id"])

        # First check if the document belongs to the current user
        document = await db.document_uploads.find_one(
            {"_id": obj_id, "user_id": user_id}, {"_id": 1}
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        await db.document_uploads.update_one(
            {"_id": obj_id}, {"$set": {"note": Note(content=content.content)}}
        )

        return NoteResponse(content=content.content)
    except HTTPException as e:
        raise e
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Error saving note: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while saving the note"
        )


@router.get("/document-uploads/{document_upload_id}/note", response_model=NoteResponse)
async def get_note(
    document_upload_id: str,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    try:
        obj_id = ObjectId(document_upload_id)
        user_id = ObjectId(current_user["_id"])

        document = await db.document_uploads.find_one(
            {"_id": obj_id, "user_id": user_id}, {"note": 1}
        )
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        note_content = ""
        if document.get("note") and isinstance(document["note"], dict):
            note_content = document["note"].get("content", "")

        return NoteResponse(content=note_content)
    except HTTPException as e:
        raise e
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Error retrieving note: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while retrieving the note"
        )


@router.patch(
    "/document-uploads/{document_id}",
    response_model=DocumentRetrieveResponse,
)
async def update_document(
    document_id: str,
    update_data: DocumentUpdateRequest,
    db: TypedAsyncIOMotorDatabase = Depends(get_db),
    current_user: MongoUser = Depends(get_current_user),
):
    """
    Update document properties.

    Currently supports:
    - custom_title: Custom title for the document
    """
    try:
        obj_id = ObjectId(document_id)
        user_id = ObjectId(current_user["_id"])

        # First check if the document belongs to the current user
        document_check = await db.document_uploads.find_one(
            {"_id": obj_id, "user_id": user_id}, {"_id": 1}
        )

        if not document_check:
            raise HTTPException(status_code=404, detail="Document not found")

        # Build update dictionary based on provided fields
        update_dict = {}
        if update_data.custom_title is not None:
            update_dict["custom_title"] = update_data.custom_title

        # If no fields to update, return 400
        if not update_dict:
            raise HTTPException(
                status_code=400,
                detail="No valid fields to update. Supported fields: custom_title",
            )

        # Update document
        await db.document_uploads.update_one({"_id": obj_id}, {"$set": update_dict})

        # Retrieve the updated document to return
        document = await db.document_uploads.find_one(
            {"_id": obj_id},
            {
                "_id": 1,
                "file_details": 1,
                "custom_title": 1,
                "extracted_metadata": 1,
                "note": 1,
            },
        )

        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Generate presigned URL
        try:
            if (
                document["file_details"]["s3_bucket"]
                == AllowedS3Buckets.PUBLIC_BUCKET.value
            ):
                presigned_url = document["file_details"]["s3_url"]
            else:
                presigned_url = generate_presigned_url(
                    document["file_details"], s3_client
                )
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error generating pre-signed URL: {str(e)}"
            )

        display_title = get_display_title(document)

        return DocumentRetrieveResponse(
            id=str(document["_id"]),
            file_name=document["file_details"]["file_name"],
            url_friendly_file_name=document["file_details"]["url_friendly_file_name"],
            file_type=document["file_details"]["file_type"],
            presigned_url=presigned_url,
            note=note_to_response(document.get("note")),
            custom_title=document.get("custom_title"),
            title=display_title,
        )
    except HTTPException as e:
        raise e
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")
    except Exception as e:
        logger.error(f"Error updating document: {str(e)}")
        raise HTTPException(
            status_code=500, detail="An error occurred while updating the document"
        )
