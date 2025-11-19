from datetime import datetime
from pydantic import (
    BaseModel,
    Field,
    UUID4
)

class UserCreate(BaseModel):
    email: str
    username: str = Field(..., max_length=32)
    password: str = Field(..., min_length=6)

    class Config:
        from_attributes=True
        orm_mode = True

class UserResponse(BaseModel):
    id: UUID4
    email: str
    username: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes=True
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str