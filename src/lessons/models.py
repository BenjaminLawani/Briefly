import uuid
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

from src.common.db import Base

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True, index=True)
    title = Column(String(32), nullable=False)
    is_deleted = Column(Boolean(), default=False)
    created_by = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)