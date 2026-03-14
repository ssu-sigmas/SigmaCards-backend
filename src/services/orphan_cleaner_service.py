from __future__ import annotations

import logging

from src.db.database import SessionLocal
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class OrphanCleanerService:
    @classmethod
    def run_once(cls) -> int:
        db = SessionLocal()
        try:
            deleted = ImageService.cleanup_orphan_images(db)
            logger.info("Orphan image cleanup finished, deleted=%s", deleted)
            return deleted
        except Exception:
            db.rollback()
            logger.exception("Orphan image cleanup failed")
            raise
        finally:
            db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    OrphanCleanerService.run_once()


if __name__ == "__main__":
    main()