from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.dependencies import get_current_user
from src.db.database import get_db
from src.models import User
from src.schemas.image import ImageUploadUrlRequest, ImageUploadUrlResponse
from src.services.image_service import ImageService

router = APIRouter(prefix="/images", tags=["images"])


@router.post("/", response_model=ImageUploadUrlResponse, status_code=status.HTTP_201_CREATED)
def get_upload_url(
    request: ImageUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ImageService.request_upload_url(db, request.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))