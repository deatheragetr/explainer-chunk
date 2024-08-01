from fastapi import APIRouter, HTTPException, Path
from bson import ObjectId
from config.s3 import s3_client
from config.environment import WasabiSettings
from api.requests.upload import (
    InitiateMultipartUploadRequest,
    GetUploadUrlRequest,
    CompleteMultipartUploadRequest,
)
from api.responses.upload import InitiateMultipartUploadResponse, GetUploadUrlResponse
from typing import Annotated
from botocore.exceptions import ClientError
from api.utils.url_friendly import make_url_friendly

settings = WasabiSettings()
router = APIRouter()


@router.post("/multipart-upload/", response_model=InitiateMultipartUploadResponse)
async def initiate_multipart_upload(request: InitiateMultipartUploadRequest):
    try:
        url_friendly_file_name = make_url_friendly(request.file_name)
        file_key = f"document_uploads/{ObjectId()}-{url_friendly_file_name}"
        response = s3_client.create_multipart_upload(
            Bucket=settings.wasabi_document_bucket,
            Key=file_key,
            ContentType=request.file_type,
        )
        return InitiateMultipartUploadResponse(
            upload_id=response["UploadId"], file_key=file_key
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-url/", response_model=GetUploadUrlResponse)
async def get_upload_url(request: GetUploadUrlRequest):
    try:
        url = s3_client.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": settings.wasabi_document_bucket,
                "Key": request.file_key,
                "UploadId": request.upload_id,
                "PartNumber": request.part_number,
            },
            ExpiresIn=3600,  # In seconds (1 hour)
        )
        return GetUploadUrlResponse(presigned_url=url)
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/multipart-upload/{upload_id}")
async def complete_multipart_upload(
    request: CompleteMultipartUploadRequest,
    upload_id: Annotated[
        str, Path(description="Upload ID of already initiated multipart upload")
    ],
):
    try:
        s3_client.complete_multipart_upload(
            Bucket=settings.wasabi_document_bucket,
            Key=request.file_key,
            UploadId=upload_id,
            MultipartUpload={"Parts": request.parts},
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
