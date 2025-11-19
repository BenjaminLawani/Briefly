import random
import string

from datetime import (
    datetime,
    timedelta,
    UTC
)

from passlib.context import CryptContext

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

ctx = CryptContext(schemes=["bcrypt"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _truncate_to_bytes(s: str, max_bytes: int = 72) -> str:
    """Truncate a string so its UTF-8 encoding is at most `max_bytes` long.

    This preserves valid UTF-8 by decoding with 'ignore' if the last character
    would otherwise be partial.
    """
    if s is None:
        return s
    b = s.encode("utf-8")
    if len(b) <= max_bytes:
        return s
    truncated = b[:max_bytes]
    return truncated.decode("utf-8", errors="ignore")


def hash_password(plain: str) -> str:
    safe_plain = _truncate_to_bytes(plain, 72)
    return ctx.hash(safe_plain)


def verify_password(plain: str, hashed: str) -> bool:
    safe_plain = _truncate_to_bytes(plain, 72)
    return ctx.verify(safe_plain, hashed)

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