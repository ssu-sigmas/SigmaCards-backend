# src/services/review_service.py
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from src.models import UserCard, ReviewLog, User, Flashcard
from src.schemas.review import ReviewRequest, ReviewResponse, DueCardResponse
from uuid import UUID
from fsrs import Scheduler, Card, Rating
import math

scheduler = Scheduler()


class ReviewService:
    @staticmethod
    def get_due_cards(db: Session, current_user: User, deck_id: UUID = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Получить карточки на повтор СЕГОДНЯ"""
        now = datetime.now(timezone.utc)
        
        query = db.query(UserCard).filter(
            UserCard.user_id == current_user.id,
            UserCard.due <= now
        )
        
        if deck_id:
            query = query.join(Flashcard).filter(Flashcard.deck_id == deck_id)
        
        cards = query.order_by(UserCard.due).limit(limit).all()
        
        response = []
        for uc in cards:
            card = db.query(Flashcard).filter(Flashcard.id == uc.card_id).first()
            response.append({
                "user_card_id": uc.id,
                "card_id": uc.card_id,
                "content": card.content,
                "state": uc.state,
                "stability": float(uc.stability),
                "difficulty": float(uc.difficulty),
                "due": uc.due.isoformat()
            })
        return response
    
    @staticmethod
    def _to_utc_datetime(dt: datetime) -> datetime:
        """Приводит datetime к UTC timezone-aware"""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    
    @staticmethod
    def submit_review(
        db: Session, 
        user_card_id: UUID, 
        rating: int,
        duration_ms: int,
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
        
        now = datetime.now(timezone.utc)
        last_review_utc = ReviewService._to_utc_datetime(user_card.last_review) if user_card.last_review else None
        due_utc = ReviewService._to_utc_datetime(user_card.due) if user_card.due else now
        
        # Правильные параметры для fsrs-py Card
        fsrs_card = Card(
            due=due_utc,
            stability=max(float(user_card.stability), 0.1),
            difficulty=max(float(user_card.difficulty), 1.0),
            state=user_card.state,
            last_review=last_review_utc
        )
        
        rating_enum = Rating(rating)
        new_fsrs_card, fsrs_review_log = scheduler.review_card(fsrs_card, rating_enum, now)
        
        # Сохраняем старое состояние
        state_before = user_card.state
        
        # Обновляем UserCard новыми значениями из FSRS
        user_card.due = new_fsrs_card.due
        user_card.stability = new_fsrs_card.stability
        user_card.difficulty = new_fsrs_card.difficulty
        user_card.state = int(new_fsrs_card.state)
        user_card.elapsed_days = getattr(new_fsrs_card, 'elapsed_days', 0)
        user_card.scheduled_days = getattr(new_fsrs_card, 'scheduled_days', 0)
        user_card.last_review = now
        
        # Логируем в БД (только поля, которые есть в модели ReviewLog)
        review_log_db = ReviewLog(
            user_id=current_user.id,
            user_card_id=user_card_id,
            rating=rating,
            state_before=state_before,
            due_after=user_card.due,
            stability_after=user_card.stability,
            difficulty_after=user_card.difficulty,
            duration_ms=duration_ms,
            review_datetime=now
        )
        
        db.add(review_log_db)
        db.commit()
        db.refresh(user_card)
        
        return ReviewResponse(
            user_card_id=user_card_id,
            new_state=user_card.state,
            next_due=user_card.due.isoformat(),
            stability=user_card.stability,
            difficulty=user_card.difficulty,
            message=f"Next review: {user_card.due.strftime('%Y-%m-%d %H:%M UTC')}"
        )
    
    @staticmethod
    def get_review_history(db: Session, user_card_id: UUID, current_user: User) -> List[ReviewLog]:
        """История повторений карточки"""
        logs = db.query(ReviewLog).filter(
            ReviewLog.user_id == current_user.id,
            ReviewLog.user_card_id == user_card_id
        ).order_by(ReviewLog.review_datetime.desc()).all()
        return logs
