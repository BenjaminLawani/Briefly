import json
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from pymongo import MongoClient
from groq import GroqError, AsyncGroq
from google.genai import Client
from sqlalchemy.orm import Session

from .config import settings
from src.common.enums import LearningType
from src.onboarding.models import Profile

# Initialize clients
mongo_client = MongoClient(settings.MONGODB_URL)
gemini_client = Client(api_key=settings.GEMINI_API_KEY)
groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

db_mongo = mongo_client[settings.MONGODB_DATABASE]
collection = db_mongo[settings.MONGODB_COLLECTION]


async def generate_lesson_content(
    user_id: str,
    db_session: Session,
    lesson_title: Optional[str] = None,
    num_of_lessons: int = 5
) -> Dict[str, Any]:
    """
    Generate lesson content based on user's onboarding preferences.
    Routes to Groq for TEXT learning type, Gemini for others.
    
    Args:
        user_id: UUID of the user
        db_session: SQLAlchemy database session
        lesson_title: Optional specific lesson title
        num_of_lessons: Number of lessons to generate (default: 5)
        
    Returns:
        Dictionary containing the generated lesson content and metadata
    """
    
    # Fetch user's onboarding profile
    profile = db_session.query(Profile).filter(
        Profile.user_id == user_id
    ).first()
    
    # If the user hasn't completed onboarding yet, create a minimal default profile
    # so we can still generate generic lessons. This helps the dashboard render
    # initial lessons for users who didn't finish onboarding.
    if not profile:
        try:
            user_uuid = uuid.UUID(user_id)
        except Exception:
            user_uuid = user_id

        default_profile = Profile(
            learning_type=LearningType.TEXT,
            topics=["general"],
            goal=None,
            user_id=user_uuid,
        )

        try:
            db_session.add(default_profile)
            db_session.commit()
            db_session.refresh(default_profile)
            profile = default_profile
        except Exception:
            # If saving a default profile fails for any reason, raise the original
            # not-found error so the caller can handle it.
            raise ValueError(f"No onboarding profile found for user {user_id}")
    
    # Extract profile data
    learning_type = profile.learning_type
    topics = profile.topics
    goal = profile.goal
    
    # Build prompt based on user preferences
    prompt = build_lesson_prompt(
        topics=topics,
        goal=goal,
        learning_type=learning_type,
        lesson_title=lesson_title,
        num_of_lessons=num_of_lessons
    )
    
    # Route to appropriate AI model
    if learning_type == LearningType.TEXT:
        lesson_content = await generate_with_groq(prompt, num_of_lessons)
    else:
        # VISUAL or AUDIO learning types use Gemini
        lesson_content = await generate_with_gemini(prompt, learning_type, num_of_lessons)
    
    # Prepare document for MongoDB
    lesson_document = {
        "_id": str(uuid.uuid4()),
        "user_id": str(user_id),
        "learning_type": learning_type.value,
        "topics": topics,
        "goal": goal,
        "num_of_lessons": num_of_lessons,
        "lessons": lesson_content.get("lessons", []),
        "created_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(days=90)
    }
    
    # Save to MongoDB
    result = collection.insert_one(lesson_document)
    
    return {
        "lesson_id": lesson_document["_id"],
        "num_of_lessons": num_of_lessons,
        "lessons": lesson_content.get("lessons", []),
        "learning_type": learning_type.value,
        "created_at": lesson_document["created_at"].isoformat()
    }


def build_lesson_prompt(
    topics: list,
    goal: Optional[str],
    learning_type: LearningType,
    lesson_title: Optional[str] = None,
    num_of_lessons: int = 5
) -> str:
    """Build a tailored prompt based on user preferences."""
    
    topics_str = ", ".join(topics) if isinstance(topics, list) else str(topics)
    
    prompt = f"Create {num_of_lessons} comprehensive lessons on the following topics: {topics_str}."
    
    if goal:
        prompt += f"\n\nThe user's learning goal is: {goal}"
    
    if lesson_title:
        prompt += f"\n\nFocus specifically on: {lesson_title}"
    
    # Tailor instructions based on learning type
    if learning_type == LearningType.TEXT:
        prompt += "\n\nProvide detailed text-based explanations with examples and exercises."
    elif learning_type == LearningType.VISUAL:
        prompt += "\n\nInclude descriptions for diagrams, visual aids, and step-by-step visual guides."
    elif learning_type == LearningType.AUDIO:
        prompt += "\n\nStructure the content in a conversational, audio-friendly format with clear narration points."
    
    prompt += """\n\nIMPORTANT: Return your response as a valid JSON object with this exact structure:
{
  "lessons": [
    {
      "lesson_number": 1,
      "title": "Lesson Title",
      "description": "Brief description",
      "content": "Full lesson content",
      "key_points": ["point 1", "point 2"],
      "exercises": ["exercise 1", "exercise 2"]
    }
  ]
}

Return ONLY the JSON object, no additional text or markdown formatting."""
    
    return prompt


async def generate_with_groq(prompt: str, num_of_lessons: int) -> Dict[str, Any]:
    """Generate lesson content using Groq API."""
    
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert educator creating engaging and comprehensive lesson content. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        
        # Parse JSON response
        lesson_data = json.loads(content)
        
        # Validate expected structure
        if "lessons" not in lesson_data:
            raise ValueError("Invalid response format: missing 'lessons' key")
        
        return lesson_data
        
    except GroqError as e:
        raise Exception(f"Groq API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Groq response as JSON: {str(e)}")


async def generate_with_gemini(prompt: str, learning_type: LearningType, num_of_lessons: int) -> Dict[str, Any]:
    """Generate lesson content using Google Gemini API."""
    
    try:
        # Configure based on learning type
        system_instruction = "You are an expert educator creating engaging lesson content. Always respond with valid JSON only."
        
        if learning_type == LearningType.VISUAL:
            system_instruction += " Focus on visual learning with clear descriptions of diagrams and imagery."
        elif learning_type == LearningType.AUDIO:
            system_instruction += " Create content optimized for audio narration and listening."
        
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=prompt,
            config={
                "temperature": 0.7,
                "max_output_tokens": 4096,
                "system_instruction": system_instruction,
                "response_mime_type": "application/json"
            }
        )
        
        content = response.text
        
        # Parse JSON response
        lesson_data = json.loads(content)
        
        # Validate expected structure
        if "lessons" not in lesson_data:
            raise ValueError("Invalid response format: missing 'lessons' key")
        
        return lesson_data
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Gemini response as JSON: {str(e)}")
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")


def generate_lesson_content_sync(
    user_id: str,
    db_session: Session,
    lesson_title: Optional[str] = None,
    num_of_lessons: int = 5
) -> Dict[str, Any]:
    """Synchronous wrapper for generate_lesson_content."""
    import asyncio
    return asyncio.run(
        generate_lesson_content(user_id, db_session, lesson_title, num_of_lessons)
    )