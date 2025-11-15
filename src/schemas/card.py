# src/schemas/card.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class CardType(str, Enum):
    BASIC = "basic"
    CLOZE = "cloze" 
    MULTI_CHOICE = "multi_choice"

class FlashcardCreate(BaseModel):
    content: Dict[str, Any] = Field(..., description="JSON с front/back/image/media")
    position: Optional[int] = Field(0, ge=0)

class FlashcardUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = Field(None)
    position: Optional[int] = Field(None, ge=0)
    is_suspended: Optional[bool] = Field(None)

class FlashcardResponse(BaseModel):
    id: UUID
    deck_id: UUID
    source_id: Optional[UUID]
    card_type: CardType
    content: Dict[str, Any]
    position: int
    is_suspended: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
