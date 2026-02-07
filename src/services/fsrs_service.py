from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from fsrs import Card, Rating, ReviewLog, Scheduler
from src.core.config import settings
from src.models import ReviewLog as DbReviewLog, User

logger = logging.getLogger(__name__)

from fsrs import Optimizer


class FsrsService:
    DEFAULT_SETTINGS = {
        "desired_retention": settings.FSRS_DESIRED_RETENTION,
    }

    @staticmethod
    def create_initial_card() -> Card:
        return Card()

    @staticmethod
    def build_scheduler(user: User) -> Scheduler:
        fsrs_settings = user.fsrs_settings or {}
        parameters = fsrs_settings.get("parameters")
        desired_retention = fsrs_settings.get("desired_retention", settings.FSRS_DESIRED_RETENTION)

        if parameters:
            return Scheduler(parameters=tuple(parameters), desired_retention=desired_retention)

        return Scheduler(desired_retention=desired_retention)

    @staticmethod
    def restore_card(*, due: datetime | None, stability: float, difficulty: float, state: int, step: int | None, last_review: datetime | None) -> Card:
        due_utc = FsrsService.to_utc(due) or datetime.now(timezone.utc)
        last_review_utc = FsrsService.to_utc(last_review)
        safe_state = max(state, 1)

        kwargs = {
            "due": due_utc,
            "state": safe_state,
            "step": step if safe_state in (1, 3) else None,
            "last_review": last_review_utc,
        }

        if stability > 0:
            kwargs["stability"] = float(stability)
        if difficulty > 0:
            kwargs["difficulty"] = float(difficulty)

        return Card(**kwargs)

    @staticmethod
    def to_utc(dt: datetime | None) -> datetime | None:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def optimize_user(user: User, review_logs: Iterable[DbReviewLog]) -> dict | None:
        logs = list(review_logs)
        if len(logs) < settings.FSRS_OPTIMIZER_MIN_REVIEWS:
            return None

        card_id_map: dict[str, int] = {}
        optimizer_logs: list[ReviewLog] = []
        for log in sorted(logs, key=lambda item: item.review_datetime):
            key = str(log.user_card_id)
            card_id_map.setdefault(key, len(card_id_map) + 1)
            optimizer_logs.append(
                ReviewLog(
                    card_id=card_id_map[key],
                    rating=Rating(log.rating),
                    review_datetime=FsrsService.to_utc(log.review_datetime),
                    review_duration=log.duration_ms,
                )
            )

        optimizer = Optimizer(optimizer_logs)
        parameters = list(optimizer.compute_optimal_parameters())
        desired_retention = float(optimizer.compute_optimal_retention(parameters))

        optimized_settings = {
            **(user.fsrs_settings or {}),
            "parameters": parameters,
            "desired_retention": desired_retention,
            "optimized_at": datetime.now(timezone.utc).isoformat(),
            "review_log_count": len(optimizer_logs),
        }
        return optimized_settings