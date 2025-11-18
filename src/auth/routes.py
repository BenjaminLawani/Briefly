from uuid import UUID

from sqlalchemy.orm import Session

from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Request,
)

from fastapi.security import OAuth2PasswordRequestForm

from .models import User
from .schemas import (
    UserCreate,
    UserResponse,
    Token
)

from src.common.config import templates
from src.common.db import get_db

from src.common.security import (
    create_access_token,
    hash_password,
    verify_password,
)

auth_router = APIRouter(
    prefix="/auth",
    tags=["AUTHENTICATION"]
)

@auth_router.post("/login", response_model=Token)
def login(
    req: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(
        (User.email == form_data.username) |
        (User.username == form_data.username)
    ).first()

    if not db_user or not verify_password(form_data.password, db_user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Credentials"
        )
    
    access_token = create_access_token(
        {
            "sub": str(db_user.id),
            "email": db_user.email
        }
    )

    db_user.user_last_login_ip = req.client.host
    db.commit()
    db.refresh(db_user)

    return {
        "access_token": access_token,
        "token_type": "Bearer"
    }

@auth_router.post("/get-started", response_model=UserResponse)
def signup(
    req: Request,
    user: UserCreate,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        (User.email == user.email) |
        (User.username == user.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail= "Email/Username already registered"
        )
    try:
        new_user = User(**user.model_dump(exclude_unset=True))
        new_user.password = hash_password(user.password)
        new_user.user_last_login_ip = req.client.host
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return UserResponse.from_orm(new_user)
    
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error: {e} occurred!"
        )
    

@auth_router.get("/login")
def get_login(req: Request):
    return templates.TemplateResponse("login.html", {"request": req})

@auth_router.get("/get-started")
def get_login(req: Request):
    return templates.TemplateResponse("get-started.html", {"request": req})