# src/schemas/card.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List, Union, Literal, Annotated
from enum import Enum

class TextBlock(BaseModel):
    id: str
    type: Literal['text']
    content: str
    meta: Optional[Dict[str, Any]] = None # adhoc для гибкости (мало ли...)

class ImageBlock(BaseModel):
    id: str
    type: Literal['image']
    image_id: str

Block = Annotated[Union[TextBlock, ImageBlock], Field(discriminator="type")]

class CardContent(BaseModel):
    front: List[Block]
    back: List[Block]

class FlashcardCreate(BaseModel):
    content: CardContent = Field(..., description="JSON карточки (back/front)")
    position: Optional[int] = Field(0, ge=0)
    source_id: Optional[UUID] = Field(None, description="ID источника карточки (опционально)")

class FlashcardUpdate(BaseModel):
    version: int = Field(..., ge=1, description="Ожидаемая версия сущности (optimistic locking)")
    content: Optional[CardContent] = Field(None)
    position: Optional[int] = Field(None, ge=0)
    is_suspended: Optional[bool] = Field(None)

class FlashcardResponse(BaseModel):
    id: UUID
    deck_id: UUID
    source_id: Optional[UUID]
    content: CardContent
    position: int
    is_suspended: bool
    version: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class GenerateCardsRequest(BaseModel):
    text: str = Field(..., description="Текст для генерации карточек")
    count: int = Field(5, ge=1, le=20, description="Количество карточек (1-20)")

class MLGeneratedCard(BaseModel):
    content: CardContent