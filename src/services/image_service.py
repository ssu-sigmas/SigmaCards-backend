from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.core.config import settings
from src.models import Image, CardImage, Flashcard
from src.services.storage_service import StorageService
from src.schemas.card import CardContentWrite, ImageBlockWrite, CardContentRead, ImageBlockRead, WriteBlock, ReadBlock


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
            "image_id": image_id,
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
    
    @staticmethod 
    def extract_ids_from_content(content: CardContentWrite) -> set[UUID]:
        image_ids: set[UUID] = set()

        for block in [*content.front, *content.back]:
            if isinstance(block, ImageBlockWrite):
                image_ids.add(block.image_id)

        return image_ids

    @staticmethod
    def sync_card_images(db: Session, card: Flashcard, image_ids: set[UUID]) -> None:
        if not image_ids:
            db.query(CardImage).filter(CardImage.card_id == card.id).delete(synchronize_session=False)
            return

        existing_images = db.query(Image.id).filter(Image.id.in_(image_ids)).all()
        existing_image_ids = {row[0] for row in existing_images}

        missing_image_ids = image_ids - existing_image_ids
        if missing_image_ids:
            missing = ", ".join(sorted(str(image_id) for image_id in missing_image_ids))
            raise ValueError(f"Some images do not exist: {missing}")

        current_links = db.query(CardImage).filter(CardImage.card_id == card.id).all()
        current_image_ids = {link.image_id for link in current_links}

        to_add = image_ids - current_image_ids
        to_remove = current_image_ids - image_ids

        for image_id in to_add:
            db.add(CardImage(card_id=card.id, image_id=image_id))

        if to_remove:
            db.query(CardImage).filter(
                CardImage.card_id == card.id,
                CardImage.image_id.in_(to_remove)
            ).delete(synchronize_session=False)

    @staticmethod
    def enrich_content_with_urls(
        db: Session,
        content: CardContentWrite
    ) -> CardContentRead:
        image_ids = ImageService.extract_ids_from_content(content)

        if not image_ids:
            return CardContentRead(
                front=content.front,
                back=content.back
            )

        rows = (
            db.query(Image.id, Image.object_name)
            .filter(Image.id.in_(image_ids))
            .all()
        )

        image_url_by_id = {
            image_id: StorageService.get_public_object_url(object_name)
            for image_id, object_name in rows
        }

        def transform(block: WriteBlock) -> ReadBlock:
            if isinstance(block, ImageBlockWrite):
                url = image_url_by_id.get(block.image_id)
                if not url:
                    raise ValueError(f"Image {block.image_id} not found")

                return ImageBlockRead(
                    id=block.id,
                    type="image",
                    image_url=url
                )

            return block

        return CardContentRead(
            front=[transform(b) for b in content.front],
            back=[transform(b) for b in content.back],
        )