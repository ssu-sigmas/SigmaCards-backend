# src/schemas/review.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class ReviewRequest(BaseModel):
    rating: int = Field(..., ge=1, le=4, description="1=Again, 2=Hard, 3=Good, 4=Easy")
    duration_ms: int = Field(default=0, ge=0, description="Время ответа в миллисекундах")

class ReviewResponse(BaseModel):
    user_card_id: UUID
    new_state: int  # 0-3
    next_due: datetime
    stability: float
    difficulty: float
    message: str

class DueCardResponse(BaseModel):
    user_card_id: UUID
    card_id: UUID
    content: Dict[str, Any]
    state: int
    stability: float
    difficulty: float
