# src/schemas/card.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class CardType(str, Enum):
    KEY_TERMS = "key_terms"
    FACTS = "facts" 
    FILL_BLANK = "fill_blank"
    TEST_QUESTIONS = "test_questions"
    CONCEPTS = "concepts"

class FlashcardCreate(BaseModel):
    content: Dict[str, Any] = Field(..., description="JSON с front/back/image/media")
    position: Optional[int] = Field(0, ge=0)
    card_type: CardType = Field(CardType.KEY_TERMS, description="Тип карточки")
    source_id: Optional[UUID] = Field(None, description="ID источника карточки (опционально)")

class FlashcardUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = Field(None)
    position: Optional[int] = Field(None, ge=0)
    card_type: Optional[CardType] = None
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

class GenerateCardsRequest(BaseModel):
    text: str = Field(..., description="Текст для генерации карточек")
    count: int = Field(5, ge=1, le=20, description="Количество карточек (1-20)")

class MLGeneratedCard(BaseModel):
    content: Dict[str, Any]
    card_type: CardType