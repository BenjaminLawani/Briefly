from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl # Added HttpUrl for URL validation

from src.common.enums import LearningType

class LessonRequest(BaseModel):
    """Request model for generating lessons."""
    # user_id is removed from here as it's provided by current_user dependency
    lesson_title: Optional[str] = Field(None, description="Specific lesson title/focus")
    num_of_lessons: int = Field(5, ge=1, le=20, description="Number of lessons to generate (1-20)")


# New schema for the content details within a lesson item
class LessonContentDetail(BaseModel):
    content_type: LearningType = Field(..., description="Type of content: VIDEO, AUDIO, or TEXT")
    content_url: Optional[HttpUrl] = Field(None, description="URL for video or audio content")
    content_text: Optional[str] = Field(None, description="Text content for TEXT lessons")
    poster_image: Optional[HttpUrl] = Field(None, description="Thumbnail URL for video/audio content")


class LessonItem(BaseModel):
    """Individual sub-lesson structure within a generated batch."""
    lesson_number: int
    title: str
    description: str
    duration: str = Field(..., description="Estimated duration (e.g., '8 min', '10 min read')")
    difficulty: str = Field(..., description="Difficulty level (e.g., 'Beginner', 'Intermediate')")
    tags: List[str] = Field(..., description="Relevant tags for the lesson")
    
    # This field now holds the detailed content structure
    content: LessonContentDetail

    # Optional fields that the LLM might generate but are not always rendered directly
    key_points: Optional[List[str]] = None
    exercises: Optional[List[str]] = None


class LessonResponse(BaseModel):
    """Response model for a batch of generated lessons."""
    lesson_id: str
    num_of_lessons: int
    lessons: List[LessonItem] # Updated to use the new LessonItem
    learning_type: LearningType # Ensure LearningType enum is used directly
    created_at: str
