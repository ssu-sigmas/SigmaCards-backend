from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.orm import Session

from src.core.config import settings
from src.models import Image, CardImage
from src.services.storage_service import StorageService


class ImageService:
    @staticmethod
    def request_upload_url(db: Session, content_type: str) -> dict:
        image_id = uuid4()
        extension = {
            "image/png": "png",
            "image/jpeg": "jpg",
            "image/webp": "webp",
        }.get(content_type)
        if not extension:
            raise ValueError("Unsupported MIME type")

        object_name = f"card-images/{image_id}.{extension}"

        image = Image(id=image_id, object_name=object_name, created_at=datetime.utcnow())
        db.add(image)
        db.commit()

        upload_payload = StorageService.generate_upload_url(object_name, content_type)
        return {
            "upload_url": upload_payload["upload_url"],
            "object_name": object_name,
            "expires_in": upload_payload["expires_in"],
            "method": upload_payload["method"],
            "upload_fields": upload_payload["upload_fields"],
            "required_headers": upload_payload["required_headers"],
        }

    @staticmethod
    def cleanup_orphan_images(db: Session) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=settings.IMAGE_ORPHAN_CLEANUP_AGE_HOURS)
        orphans = db.query(Image).outerjoin(CardImage, CardImage.image_id == Image.id).filter(
            CardImage.image_id.is_(None),
            Image.created_at < cutoff
        ).all()

        deleted = 0
        for image in orphans:
            try:
                StorageService.delete_object(image.object_name)
            except Exception as e:
                print(e, flush=True)
                continue
            db.delete(image)
            deleted += 1

        db.commit()
        return deleted