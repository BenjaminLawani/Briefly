import os
from dotenv import load_dotenv

from fastapi.templating import Jinja2Templates

from pydantic_settings import BaseSettings

load_dotenv()

templates = Jinja2Templates(directory="templates")

class Config(BaseSettings):
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    JWT_KEY: str = os.environ["JWT_KEY"]
    GROQ_API_KEY: str = os.environ["GROQ_API_KEY"]
    GEMINI_API_KEY: str = os.environ["GEMINI_API_KEY"]
    MONGODB_DATABASE: str = os.environ["MONGODB_DATABASE"]
    MONGODB_COLLECTION: str = os.environ["MONGODB_COLLECTION"]
    MONGODB_URL: str = os.environ["MONGODB_URL"]

settings = Config()