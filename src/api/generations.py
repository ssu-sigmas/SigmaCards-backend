from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID

from src.core.dependencies import get_current_user
from src.db.database import get_db
from src.models import User
from src.schemas.card import CardContentRead
from src.schemas.generation import GenerationSummaryResponse, GenerationDetailsResponse, GenerationCardResponse
from src.services.generation_service import GenerationService

router = APIRouter(prefix="/generations", tags=["generations"])


@router.get("", response_model=list[GenerationSummaryResponse])
def list_generations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GenerationService.list_user_generations(db, current_user, skip, limit)


@router.get("/{generation_id}", response_model=GenerationDetailsResponse)
def get_generation(
    generation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        generation = GenerationService.get_user_generation(db, generation_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    cards = [
        GenerationCardResponse(
            id=card.id,
            position=card.position,
            content=CardContentRead.model_validate(card.content),
            created_at=card.created_at,
        )
        for card in sorted(generation.cards, key=lambda c: c.position)
    ]

    return GenerationDetailsResponse(
        id=generation.id,
        requested_count=generation.requested_count,
        generated_count=generation.generated_count,
        is_stopped=generation.is_stopped,
        created_at=generation.created_at,
        completed_at=generation.completed_at,
        cards=cards,
    )