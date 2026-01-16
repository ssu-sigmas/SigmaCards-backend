from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from enum import Enum

class DeckStatus(str, Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    SHARED = "shared"

class DeckCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class DeckUpdate(BaseModel):
    version: int = Field(..., ge=1, description="Ожидаемая версия сущности (optimistic locking)")
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[DeckStatus] = None

class DeckResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: Optional[str]
    status: DeckStatus
    version: int
    created_at: datetime
    updated_at: datetime
    flashcards_count: int = 0  # Кол-во карточек (посчитаем в сервисе)
    
    class Config:
        from_attributes = True
