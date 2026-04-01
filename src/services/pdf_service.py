from datetime import datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from src.models import Source
from src.services.storage_service import StorageService


class PdfService:
    @staticmethod
    def request_upload_url(db: Session, user_id: uuid4, content_type: str) -> dict:
        if content_type != "application/pdf":
            raise ValueError("Unsupported MIME type")

        file_id = uuid4()
        object_name = f"source-pdfs/{file_id}.pdf"

        source = Source(
            id=file_id,
            user_id=user_id,
            type="pdf",
            content_text=None,
            file_path=object_name,
            created_at=datetime.utcnow(),
        )
        db.add(source)
        db.commit()

        upload_payload = StorageService.generate_upload_url(
            object_name=object_name,
            content_type=content_type,
            max_size_bytes=StorageService.PDF_MAX_SIZE_BYTES,
        )

        return {
            "file_id": file_id,
            "upload_url": upload_payload["upload_url"],
            "object_name": object_name,
            "expires_in": upload_payload["expires_in"],
            "method": upload_payload["method"],
            "upload_fields": upload_payload["upload_fields"],
            "required_headers": upload_payload["required_headers"],
        }