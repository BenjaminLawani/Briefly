import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    func,
)
from sqlalchemy.dialects.postgresql import (
    UUID
)

from src.common.db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), default=uuid.uuid4(),
                 primary_key=True, index=True)
    email = Column(String(128), nullable=False, unique=True)
    username = Column(String(64), nullable=False, unique=True)
    password = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                        default=func.now(), onupdate=func.now())
    user_last_login_ip = Column(String(), nullable=False)
