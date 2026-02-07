# src/services/review_service.py
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from src.models import UserCard, ReviewLog, User, Flashcard
from src.schemas.review import ReviewResponse
from uuid import UUID
from fsrs import Rating
from src.services.fsrs_service import FsrsService


class ReviewService:
    @staticmethod
    def get_due_cards(db: Session, current_user: User, deck_id: UUID = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить карточки на повтор СЕГОДНЯ"""
        now = datetime.now(timezone.utc)
        
        query = db.query(UserCard).options(joinedload(UserCard.card)).filter(
            UserCard.user_id == current_user.id,
            UserCard.due <= now
        )
        
        if deck_id:
            query = query.filter(UserCard.card.has(Flashcard.deck_id == deck_id))
        
        cards = query.order_by(UserCard.due).limit(limit).all()
        
        response = []
        for uc in cards:
            response.append({
                "user_card_id": uc.id,
                "card_id": uc.card_id,
                "content": uc.card.content,
                "state": uc.state,
                "stability": float(uc.stability),
                "difficulty": float(uc.difficulty),
                "due": uc.due.isoformat(),
                "version": uc.version,
            })
        return response
    
    @staticmethod
    def submit_review(
        db: Session, 
        user_card_id: UUID, 
        rating: int,
        duration_ms: int,
        expected_version: int,
        current_user: User
    ) -> ReviewResponse:
        """Оценить карточку и пересчитать FSRS"""
        user_card = db.query(UserCard).filter(
            UserCard.id == user_card_id,
            UserCard.user_id == current_user.id
        ).first()
        
        if not user_card:
            raise ValueError("Card not found")
        
        if rating < 1 or rating > 4:
            raise ValueError("Rating must be 1-4")
        
        if user_card.version != expected_version:
            raise ValueError("Version conflict: card has already been reviewed")
        
        now = datetime.now(timezone.utc)
        scheduler = FsrsService.build_scheduler(current_user)
        fsrs_card = FsrsService.restore_card(
            due=user_card.due,
            stability=float(user_card.stability),
            difficulty=float(user_card.difficulty),
            state=user_card.state,
            step=user_card.step,
            last_review=user_card.last_review,
        )
        rating_enum = Rating(rating)
        new_fsrs_card, _ = scheduler.review_card(fsrs_card, rating_enum, now, review_duration=duration_ms)
        state_before = user_card.state
        updated_rows = (
            db.query(UserCard)
            .filter(
                UserCard.id == user_card_id,
                UserCard.user_id == current_user.id,
                UserCard.version == expected_version,
            )
            .update(
                {
                    UserCard.due: new_fsrs_card.due,
                    UserCard.stability: new_fsrs_card.stability,
                    UserCard.difficulty: new_fsrs_card.difficulty,
                    UserCard.state: int(new_fsrs_card.state),
                    UserCard.elapsed_days: getattr(new_fsrs_card, "elapsed_days", 0),
                    UserCard.scheduled_days: getattr(new_fsrs_card, "scheduled_days", 0),
                    UserCard.last_review: now,
                    UserCard.version: expected_version + 1,
                },
                synchronize_session=False,
            )
        )

        if updated_rows == 0:
            db.rollback()
            raise ValueError("Version conflict: card has already been reviewed")

        review_log_db = ReviewLog(
            user_id=current_user.id,
            user_card_id=user_card_id,
            rating=rating,
            state_before=state_before,
            due_after=new_fsrs_card.due,
            stability_after=new_fsrs_card.stability,
            difficulty_after=new_fsrs_card.difficulty,
            duration_ms=duration_ms,
            review_datetime=now,
        )

        db.add(review_log_db)
        db.commit()

        new_user_card = db.query(UserCard).filter(UserCard.id == user_card_id).first()

        return ReviewResponse(
            user_card_id=user_card_id,
            new_state=new_user_card.state,
            next_due=new_user_card.due,
            stability=new_user_card.stability,
            difficulty=new_user_card.difficulty,
            version=new_user_card.version,
            message=f"Next review: {new_user_card.due.strftime('%Y-%m-%d %H:%M UTC')}",
        )
    
    @staticmethod
    def get_review_history(db: Session, user_card_id: UUID, current_user: User) -> List[ReviewLog]:
        """История повторений карточки"""
        logs = db.query(ReviewLog).filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.user_card_id == user_card_id
        ).order_by(ReviewLog.review_datetime.desc()).all()
        return logs
