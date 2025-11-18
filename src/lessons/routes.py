from typing import List
from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    status
)

from sqlalchemy.orm import Session

from .schemas import (
    LessonRequest,
    LessonResponse
)

from src.auth.models import User

from src.common.db import get_db
from src.common.utils import generate_lesson_content, collection
from src.common.security import get_current_user

lessons_router = APIRouter(
    prefix="/lessons",
    tags=["lessons"]
)


@lessons_router.post(
    "/generate",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_lessons(
    request: LessonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate personalized lesson content based on user's onboarding preferences.
    
    - **user_id**: UUID of the user
    - **lesson_title**: Optional specific topic to focus on
    - **num_of_lessons**: Number of lessons to generate (default: 5, max: 20)
    
    The system will:
    1. Fetch user's learning preferences from onboarding
    2. Route to Groq (TEXT) or Gemini (VISUAL/AUDIO)
    3. Generate structured lesson content
    4. Save to MongoDB and return the results
    """
    try:
        result = await generate_lesson_content(
            user_id=str(current_user.id),
            db_session=db,
            lesson_title=request.lesson_title,
            num_of_lessons=request.num_of_lessons
        )
        
        return LessonResponse(**result)
        
    except ValueError as e:
        # User profile not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        # General errors (API failures, database issues, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate lessons: {str(e)}"
        )


@lessons_router.get(
    "/{lesson_id}",
    response_model=LessonResponse,
)
async def get_lesson(
    lesson_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)

):
    """
    Retrieve a previously generated lesson by ID.
    
    - **lesson_id**: UUID of the lesson
    """
    
    try:
        lesson_doc = collection.find_one({"_id": lesson_id})
        
        if not lesson_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with id {lesson_id} not found"
            )
        
        return LessonResponse(
            lesson_id=lesson_doc["_id"],
            num_of_lessons=lesson_doc.get("num_of_lessons", len(lesson_doc.get("lessons", []))),
            lessons=lesson_doc.get("lessons", []),
            learning_type=lesson_doc["learning_type"],
            created_at=lesson_doc["created_at"].isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve lesson: {str(e)}"
        )


@lessons_router.get(
    "/user/{user_id}",
    response_model=List[LessonResponse],
)
async def get_user_lessons(
    limit: int = 10,
    skip: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)

):
    
    try:
        lessons = list(
            collection.find({"user_id": str(current_user.id)})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        if not lessons:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No lessons found for user {str(current_user.id)}"
            )
        
        return [
            LessonResponse(
                lesson_id=lesson["_id"],
                num_of_lessons=lesson.get("num_of_lessons", len(lesson.get("lessons", []))),
                lessons=lesson.get("lessons", []),
                learning_type=lesson["learning_type"],
                created_at=lesson["created_at"].isoformat()
            )
            for lesson in lessons
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user lessons: {str(e)}"
        )


@lessons_router.delete(
    "/{lesson_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_lesson(
    lesson_id: str,
    db: Session = Depends(get_db)
):
    try:
        result = collection.delete_one({"_id": lesson_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with id {lesson_id} not found"
            )
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete lesson: {str(e)}"
        )