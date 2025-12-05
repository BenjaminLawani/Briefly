from datetime import (

    datetime,
    timedelta,
    UTC
)

import bcrypt
from jwt import (
    encode,
    decode,
)

from sqlalchemy.orm import Session

from fastapi import (
    HTTPException,
    Depends,
    status,
)
from fastapi.security import OAuth2PasswordBearer

from .db import get_db
from .config import settings

from src.auth.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
def jwt_encode(data: dict) -> str:
    return encode(data, settings.JWT_KEY, algorithm="HS256")

def jwt_decode(token: str): 
    return decode(token, settings.JWT_KEY, algorithms=["HS256"])

def create_access_token(data: dict):
    to_encode = data.copy()
    expires = datetime.now(UTC) + timedelta(seconds=3599) 
    to_encode.update({"exp": expires})
    encoded = jwt_encode(to_encode)
    return encoded

def create_refresh_token(data: dict):
    to_encode = data.copy()
    expires = datetime.now(UTC) + timedelta(hours=12)
    to_encode.update({"exp": expires})
    encoded = jwt_encode(to_encode)
    return encoded

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"}    
        )
    try:

        payload = jwt_decode(token)
        email : str = payload.get("email")

        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user