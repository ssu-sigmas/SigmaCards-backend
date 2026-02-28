from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReviewFilterField(str, Enum):
    RETRIEVABILITY = "retrievability"
    STABILITY = "stability"
    DIFFICULTY = "difficulty"
    DUE = "due"
    LAST_REVIEW = "last_review"
    STATE = "state"


class NumericOperator(str, Enum):
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    GTE = "gte"
    GT = "gt"


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ReviewSortField(str, Enum):
    RETRIEVABILITY = "retrievability"
    STABILITY = "stability"
    DIFFICULTY = "difficulty"
    DUE = "due"
    LAST_REVIEW = "last_review"
    STATE = "state"
    RANDOM = "random"


class ReviewFilterReference(str, Enum):
    NOW = "now"
    # todo: somehow support queries: "all cards last reviewed some time ago (ref, not val!!!)"


class ReviewFilter(BaseModel):
    field: ReviewFilterField
    operator: NumericOperator
    value: Optional[float] = Field(default=None, description="Числовое значение фильтра. Время в Unix timestamp UTC")
    reference: Optional[ReviewFilterReference] = None

    @model_validator(mode='after')
    def validate_value(self) -> "ReviewFilter":
        if self.value is None and self.reference is None:
            raise ValueError("filter must define value or reference")
        if self.value is not None and self.reference is not None:
            raise ValueError("filter cannot define both value and reference")
        if self.reference is not None and self.field not in {ReviewFilterField.DUE, ReviewFilterField.LAST_REVIEW}:
            raise ValueError("reference is supported only for due and last_review")
        if self.value is not None and self.field == ReviewFilterField.RETRIEVABILITY and not 0 <= self.value <= 1:
            raise ValueError("retrievability filter value must be between 0 and 1")
        if self.value is not None and self.field == ReviewFilterField.STATE and self.value != int(self.value):
            raise ValueError("state filter value must be an integer")
        return self
