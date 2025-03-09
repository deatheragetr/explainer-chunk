from fastapi import APIRouter, HTTPException, Depends
from background.huey_jobs.capture_website_job import capture_website
from api.requests.website_capture import WebsiteCaptureRequest
from api.responses.website_capture import WebsiteCaptureResponse
from api.utils.auth_helper import get_current_user
from db.models.user import MongoUser

router = APIRouter()


@router.post("/capture-website/", response_model=WebsiteCaptureResponse)
async def capture_website_endpoint(
    request: WebsiteCaptureRequest,
    current_user: MongoUser = Depends(get_current_user),
):
    try:
        # Huey decorated tasks return a results object, which confuses the type checker: https://huey.readthedocs.io/en/latest/api.html#Result
        capture_website(
            request.url, request.document_upload_id, str(current_user["_id"])
        )
        return WebsiteCaptureResponse(
            url=request.url, document_upload_id=request.document_upload_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
