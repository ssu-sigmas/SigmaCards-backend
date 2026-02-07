# src/api/review.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from src.schemas.review import ReviewRequest, ReviewResponse, DueCardResponse
from src.services.review_service import ReviewService
from src.services.idempotency_service import IdempotencyService
from src.core.dependencies import get_current_user, get_idempotency_key
from src.db.database import get_db
from src.models import User, UserCard
from typing import List

router = APIRouter(prefix="/review", tags=["review"])

@router.get("/due", response_model=List[DueCardResponse])
def get_due_cards(
    deck_id: UUID = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить карточки на повтор СЕГОДНЯ
    
    Возвращает только те карточки, у которых due <= now()
    """
    try:
        cards = ReviewService.get_due_cards(db, current_user, deck_id, limit)
        return cards
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{user_card_id}", response_model=ReviewResponse)
def submit_review(
    user_card_id: UUID,
    review_data: ReviewRequest,
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: Session = Depends(get_db)
):
    """
    Оценить карточку (1-4) → FSRS пересчитает параметры
    
    rating:
    - 1 = Again (забыл)
    - 2 = Hard (было сложно)
    - 3 = Good (нормально)
    - 4 = Easy (легко)
    """
    try:
        return IdempotencyService.execute(
            namespace="review-card",
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            payload=review_data.model_dump(mode='json'),
            operation=lambda: ReviewService.submit_review(
                db, 
                user_card_id, 
                review_data.rating,
                review_data.duration_ms,
                review_data.version,
                current_user,
            ),
            response_schema=ReviewResponse,
        )
    except ValueError as e:
        detail = str(e)
        status_code = 409 if "Version conflict" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)
    except HTTPException: 
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/history/{card_id}")
def get_review_history(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю повторений карточки"""
    try:
        logs = ReviewService.get_review_history(db, card_id, current_user)
        return logs
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
