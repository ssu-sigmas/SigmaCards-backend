# src/api/cards.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from src.schemas.card import FlashcardCreate, FlashcardUpdate, FlashcardResponse
from src.services.card_service import CardService
from src.core.dependencies import get_current_user, get_idempotency_key
from src.db.database import get_db
from src.models import User
from src.schemas.card import GenerateCardsRequest, MLGeneratedCard
from src.services.idempotency_service import IdempotencyService
#from src.services.ml_service import ml_service

router = APIRouter(prefix="/cards", tags=["cards"])

@router.post("/decks/{deck_id}/cards", response_model=FlashcardResponse, status_code=status.HTTP_201_CREATED)
def create_card(
    deck_id: UUID,
    card_data: FlashcardCreate,
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: Session = Depends(get_db)
):
    """Создать карточку в колоде"""
    try:
        return IdempotencyService.execute(
            namespace=f"create-card:{deck_id}",
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            payload=card_data.model_dump(mode='json'),
            operation=lambda: CardService.create_card(db, card_data, deck_id, current_user),
            response_schema=FlashcardResponse,
        )
    except HTTPException: raise
    except ValueError as e:
        detail = str(e)
        status_code = 409 if "Version conflict" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)

@router.get("/decks/{deck_id}/cards", response_model=List[FlashcardResponse])
def get_deck_cards(
    deck_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить карточки колоды"""
    try:
        cards = CardService.get_deck_cards(db, deck_id, current_user, skip, limit)
        return cards
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{card_id}", response_model=FlashcardResponse)
def get_card(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить карточку"""
    try:
        card = CardService.get_card(db, card_id, current_user)
        return card
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{card_id}", response_model=FlashcardResponse)
def update_card(
    card_id: UUID,
    card_data: FlashcardUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить карточку"""
    try:
        card = CardService.update_card(db, card_id, card_data, current_user)
        return card
    except ValueError as e:
        detail = str(e)
        status_code = 409 if "Version conflict" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)

@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_card(
    card_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить карточку"""
    try:
        CardService.delete_card(db, card_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/generate", response_model=List[MLGeneratedCard])
async def generate_cards_ml(
    request: GenerateCardsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Генерирует карточки разных типов через ML-сервис (прослойка)
    НЕ сохраняет в БД - только возвращает для фронта
    """
    cards = await ml_service.generate_cards(request.text, request.count)
    return cards
