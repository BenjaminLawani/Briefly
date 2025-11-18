from typing import Optional, List, Dict, Any
from pydantic import BaseModel,UUID4,Field

from src.common.enums import LearningType

class LessonRequest(BaseModel):
    """Request model for generating lessons."""
    user_id: str = Field(..., description="User UUID")
    lesson_title: Optional[str] = Field(None, description="Specific lesson title/focus")
    num_of_lessons: int = Field(5, ge=1, le=20, description="Number of lessons to generate (1-20)")


class LessonItem(BaseModel):
    """Individual lesson structure."""
    lesson_number: int
    title: str
    description: str
    content: str
    key_points: List[str]
    exercises: List[str]


class LessonResponse(BaseModel):
    """Response model for generated lessons."""
    lesson_id: str
    num_of_lessons: int
    lessons: List[Dict[str, Any]]
    learning_type: str
    created_at: str