from typing import Optional, List
from pydantic import (
    BaseModel,
    UUID4,
    Field,
)
from src.common.enums import LearningType

class OnboardingRequest(BaseModel):
    learning_type: LearningType
    topics: Optional[List[str]] = None
    goal: Optional[str] = None

    class Config:
        from_attributes=True
        orm_mode = True

class OnboardingResponse(BaseModel):
    id: UUID4
    learning_type: LearningType
    topics: Optional[List[str]] = None
    goal: Optional[str] = None

    class Config:
        from_attributes=True
        orm_mode = True