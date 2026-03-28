from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.schemas.card import CardContentRead


class GenerationCardResponse(BaseModel):
    id: UUID
    position: int
    content: CardContentRead
    created_at: datetime

    class Config:
        from_attributes = True


class GenerationSummaryResponse(BaseModel):
    id: UUID
    requested_count: int
    generated_count: int
    is_stopped: bool
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class GenerationDetailsResponse(GenerationSummaryResponse):
    cards: list[GenerationCardResponse]