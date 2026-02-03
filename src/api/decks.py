from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List
from src.schemas.deck import DeckCreate, DeckUpdate, DeckResponse
from src.services.deck_service import DeckService
from src.services.idempotency_service import IdempotencyService
from src.core.dependencies import get_current_user, get_idempotency_key
from src.db.database import get_db
from src.models import User, Deck
from uuid import UUID

router = APIRouter(prefix="/decks", tags=["decks"])

@router.post("/", response_model=DeckResponse, status_code=status.HTTP_201_CREATED)
def create_deck(
    deck_data: DeckCreate,
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Depends(get_idempotency_key),
    db: Session = Depends(get_db)
):
    """Создать новую колоду"""
    def create_deck_response() -> DeckResponse:
        deck = DeckService.create_deck(db, deck_data, current_user)
        deck_response = DeckResponse.from_orm(deck)
        deck_response.flashcards_count = DeckService.get_deck_count(deck, db)
        return deck_response
    try:
        return IdempotencyService.execute(
            namespace="create-deck",
            idempotency_key=idempotency_key,
            user_id=current_user.id,
            payload=deck_data.model.dump(mode="json"),
            operation=create_deck_response,
            response_schema=DeckResponse,
        )
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[DeckResponse])
def get_user_decks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список колод пользователя"""
    decks = DeckService.get_user_decks(db, current_user, skip, limit)
    deck_counts = DeckService.get_deck_counts(db, [deck.id for deck in decks])

    deck_responses: list[DeckResponse] = []
    for deck in decks:
        deck_response = DeckResponse.from_orm(deck)
        deck_response.flashcards_count = deck_counts.get(deck.id, 0)
        deck_responses.append(deck_response)

    return deck_responses

@router.get("/{deck_id}", response_model=DeckResponse)
def get_deck(
    deck_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить информацию о колоде"""
    try:
        deck = DeckService.get_deck(db, deck_id, current_user)
        deck_response = DeckResponse.from_orm(deck)
        deck_response.flashcards_count = DeckService.get_deck_count(deck, db)
        return deck_response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{deck_id}", response_model=DeckResponse)
def update_deck(
    deck_id: UUID,
    deck_data: DeckUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить колоду"""
    try:
        deck = DeckService.update_deck(db, deck_id, deck_data, current_user)
        deck_response = DeckResponse.from_orm(deck)
        deck_response.flashcards_count = DeckService.get_deck_count(deck, db)
        return deck_response
    except ValueError as e:
        detail = str(e)
        status_code = 409 if "Version conflict" in detail else 404
        raise HTTPException(status_code=status_code, detail=detail)

@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(
    deck_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить колоду"""
    try:
        DeckService.delete_deck(db, deck_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
