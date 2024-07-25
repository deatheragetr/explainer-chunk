from fastapi import APIRouter, HTTPException
from bson import ObjectId
from config.s3 import s3_client
from config.environment import WasabiSettings
from api.requests.upload import UploadFileInfoRequest
from api.responses.upload import UploadFileInfoResponse

settings = WasabiSettings()

router = APIRouter()

@router.post("/upload-url/", response_model=UploadFileInfoResponse)
async def upload_url(file_info: UploadFileInfoRequest):
    file_key = f"{ObjectId()}-{file_info.filename}"
    try:
        presigned_url = s3_client.generate_presigned_url('put_object',
            Params={'Bucket': settings.wasabi_document_bucket, 'Key': file_key, 'ContentType': file_info.file_type},
            ExpiresIn=3600,
            HttpMethod='PUT'
        )
        return UploadFileInfoResponse(presigned_url=presigned_url, file_key=file_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
