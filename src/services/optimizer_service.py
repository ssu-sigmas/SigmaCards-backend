from __future__ import annotations

import logging

from sqlalchemy import func

from src.db.database import SessionLocal
from src.models import ReviewLog, User
from src.services.fsrs_service import FsrsService
from src.core.config import settings

logger = logging.getLogger(__name__)


class OptimizerService:
    @classmethod
    def run_once(cls) -> None:
        db = SessionLocal()
        try:
            users = (
                db.query(User)
                .join(ReviewLog, ReviewLog.user_id == User.id)
                .group_by(User.id)
                .having(func.count(ReviewLog.id) >= settings.FSRS_OPTIMIZER_MIN_REVIEWS)
                .all()
            )

            for user in users:
                logs = db.query(ReviewLog).filter(ReviewLog.user_id == user.id).all()
                optimized_settings = FsrsService.optimize_user(user, logs)
                if optimized_settings and optimized_settings != (user.fsrs_settings or {}):
                    user.fsrs_settings = optimized_settings
                    logger.info("Updated FSRS parameters for user=%s", user.id)

            db.commit()
        except Exception:
            db.rollback()
            logger.exception("FSRS optimizer run failed")
            raise
        finally:
            db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    OptimizerService.run_once()


if __name__ == "__main__":
    main()