from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.dependencies import get_current_user
from src.db.database import get_db
from src.models import User
from src.schemas.pdf import PdfUploadUrlRequest, PdfUploadUrlResponse
from src.services.pdf_service import PdfService

router = APIRouter(prefix="/pdfs", tags=["pdfs"])


@router.post("/", response_model=PdfUploadUrlResponse, status_code=status.HTTP_201_CREATED)
def get_upload_url(
    request: PdfUploadUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return PdfService.request_upload_url(db, current_user.id, request.content_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))