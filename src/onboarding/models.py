import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    JSON
)
from sqlalchemy.dialects.postgresql import (
    ENUM,
    UUID
)

from src.common.enums import LearningType
from src.common.db import Base

class Profile(Base):
    __tablename__ = "onboarding_status"
    id = Column(UUID(as_uuid=True), default=uuid.uuid4(), primary_key=True)
    learning_type = Column(ENUM(LearningType), default=LearningType.TEXT, nullable=False)
    topics = Column(JSON(), nullable=False)
    goal = Column(String(64), nullable=True)
    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)