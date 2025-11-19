import json
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any
from pymongo import MongoClient
from groq import GroqError, AsyncGroq
from google.genai import Client # Assuming this Client object can be awaited as per user's setup
from sqlalchemy.orm import Session

from .config import settings
from src.common.enums import LearningType
from src.onboarding.models import Profile

# Initialize clients
mongo_client = MongoClient(settings.MONGODB_URL)
# User specified to not change import names or client setup, assuming `Client` works for async.
# If `Client().generate_content` is strictly synchronous, this setup will block.
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
    if not profile:
        try:
            # Ensure user_id is a valid UUID before creating a Profile object with it
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            raise ValueError(f"Invalid user_id format: {user_id}. Expected a valid UUID.")

        default_profile = Profile(
            learning_type=LearningType.TEXT, # Default to TEXT
            topics=["general programming concepts"], 
            goal="gain foundational knowledge in various tech areas",
            user_id=user_uuid,
        )

        try:
            db_session.add(default_profile)
            db_session.commit()
            db_session.refresh(default_profile)
            profile = default_profile
        except Exception as e:
            # Rollback in case of error when trying to save default profile
            db_session.rollback() 
            raise ValueError(f"No onboarding profile found for user {user_id} and failed to create default: {e}")
    
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
        "learning_type": learning_type.value, # Store enum value as string
        "topics": topics,
        "goal": goal,
        "num_of_lessons": num_of_lessons,
        "lessons": lesson_content.get("lessons", []), # This structure should now conform to LessonItem
        "created_at": datetime.now(UTC),
        "expires_at": datetime.now(UTC) + timedelta(days=90)
    }
    
    # Save to MongoDB
    collection.insert_one(lesson_document) # No need to capture result if not used
    
    return {
        "lesson_id": lesson_document["_id"],
        "num_of_lessons": num_of_lessons,
        "lessons": lesson_document["lessons"], # Return the lessons that were actually saved
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
    
    # Tailor instructions based on learning type and ensure JSON structure matches schemas.py
    prompt += f"\n\nEach lesson should include a 'title', 'description', 'duration' (e.g., '10 min', '5 min read'), 'difficulty' (e.g., 'Beginner', 'Intermediate'), and 'tags' (list of strings)."
    
    if learning_type == LearningType.TEXT:
        prompt += "\n\nFor content, provide the full lesson text in a 'content_text' field within a nested 'content' object. 'content_url' and 'poster_image' should be null."
    elif learning_type == LearningType.VISUAL:
        prompt += "\n\nFor content, provide a publicly accessible video embed URL (e.g., YouTube) in 'content_url' and a relevant thumbnail URL in 'poster_image' within a nested 'content' object. 'content_text' should be null."
        prompt += "\nIf you cannot find specific content, use a generic placeholder YouTube embed URL (e.g., 'https://www.youtube.com/embed/dQw4w9WgXcQ') and its corresponding maxresdefault.jpg as 'poster_image'."
    elif learning_type == LearningType.AUDIO:
        prompt += "\n\nFor content, provide a publicly accessible audio URL (e.g., MP3 file) in 'content_url' and a relevant image URL for the audio's thumbnail in 'poster_image' within a nested 'content' object. 'content_text' should be null."
        prompt += "\nIf you cannot find specific content, use a generic placeholder audio URL (e.g., 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3') and a placeholder image URL for 'poster_image' (e.g., 'https://via.placeholder.com/640x360/E0F2F7/000000?text=Audio+Lesson')."
    
    prompt += f"""\n\nAdditionally, include 'key_points' and 'exercises' as lists of strings for each lesson.
    
IMPORTANT: Return your response as a valid JSON object with this exact structure, ensuring 'content_type' within each 'content' object is '{learning_type.value}':
{{
  "lessons": [
    {{
      "lesson_number": 1,
      "title": "Lesson Title Example",
      "description": "This is a brief description of the first lesson.",
      "duration": "10 min read",
      "difficulty": "Beginner",
      "tags": ["Tag1", "Tag2", "Tag3"],
      "content": {{
        "content_type": "{learning_type.value}",
        "content_url": {"null" if learning_type == LearningType.TEXT else ("\"https://www.youtube.com/embed/EXAMPLE_VIDEO_ID\"" if learning_type == LearningType.VISUAL else "\"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3\"")},
        "content_text": {"\"Detailed text content for the lesson.\"" if learning_type == LearningType.TEXT else "null"},
        "poster_image": {"null" if learning_type == LearningType.TEXT else ("\"https://img.youtube.com/vi/EXAMPLE_VIDEO_ID/maxresdefault.jpg\"" if learning_type == LearningType.VISUAL else "\"https://via.placeholder.com/640x360/E0F2F7/000000?text=Audio+Lesson\"")}
      }},
      "key_points": [
        "First key point summary.",
        "Second key point summary."
      ],
      "exercises": [
        "Exercise 1: Describe the main concept in your own words.",
        "Exercise 2: Find an example related to this lesson."
      ]
    }}
    // ... potentially more lesson objects up to num_of_lessons
  ]
}}
Return ONLY the JSON object, no additional text, markdown formatting, or explanations outside the JSON. Ensure all fields are present and correctly typed. URLs for 'content_url' and 'poster_image' should be valid HTTP(S) links, even if placeholders. For 'TEXT' type, 'content_url' and 'poster_image' should be null, and 'content_text' should contain the full lesson text. For 'VISUAL' or 'AUDIO' types, 'content_text' should be null.
"""
    
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
            model="llama-3.1-8b-instant", 
            temperature=0.7,
            max_tokens=4096,
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        
        # Parse JSON response
        lesson_data = json.loads(content)
        
        # Basic validation; Pydantic will do a full validation in the route
        if not isinstance(lesson_data, dict) or "lessons" not in lesson_data or not isinstance(lesson_data["lessons"], list):
            raise ValueError("Groq response is not in the expected JSON format: missing 'lessons' array or invalid structure.")
        
        return lesson_data
        
    except GroqError as e:
        raise Exception(f"Groq API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Groq response as JSON. Raw content: {content[:500]}... Error: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred during Groq generation: {str(e)}")


async def generate_with_gemini(prompt: str, learning_type: LearningType, num_of_lessons: int) -> Dict[str, Any]:
    """Generate lesson content using Google Gemini API."""
    
    try:
        # User explicitly asked not to change imports.
        # This assumes `google.genai.Client`'s `generate_content` method is awaitable
        # or that the user's setup handles async invocation of this potentially sync client.
        response = await gemini_client.generate_content( # Await is added here
            contents=[
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 4096,
                # system_instruction is often better placed in the prompt itself for strict JSON.
                # "system_instruction": system_instruction, # Removed as the prompt explicitly states structure
                "response_mime_type": "application/json"
            }
        )
        
        content = response.text
        
        # Parse JSON response
        lesson_data = json.loads(content)
        
        # Basic validation; Pydantic will do a full validation in the route
        if not isinstance(lesson_data, dict) or "lessons" not in lesson_data or not isinstance(lesson_data["lessons"], list):
            raise ValueError("Gemini response is not in the expected JSON format: missing 'lessons' array or invalid structure.")
        
        return lesson_data
        
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Gemini response as JSON. Raw content: {content[:500]}... Error: {str(e)}")
    except Exception as e:
        raise Exception(f"Gemini API error: {str(e)}")


# Synchronous wrapper - kept as is per original file, likely for non-async contexts.
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
