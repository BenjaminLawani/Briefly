from uuid import UUID
from sqlalchemy.orm import Session

from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Request,
)

from .models import Profile
from .schemas import (
    OnboardingRequest,
    OnboardingResponse
)

from src.auth.models import User

from src.common.db import get_db
from src.common.config import templates
from src.common.security import get_current_user

profile_router = APIRouter(
    prefix="/onboarding",
    tags = ["ONBOARDING"]
)

@profile_router.get("/")
def get_onboarding_page(req: Request):
    return templates.TemplateResponse("onboarding.html",{"request": req})

@profile_router.post("/", response_model=OnboardingResponse)
def create_profile(
    req: Request,
    profile: OnboardingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing_profile = db.query(Profile).filter(
        (Profile.user_id == current_user.id)
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="LMAO"
        )
    try:
        new_profile = Profile(**profile.model_dump(exclude_unset=True))
        new_profile.user_id = current_user.id
        db.add(new_profile)
        db.commit()
        db.refresh(new_profile)
        return OnboardingResponse.from_orm(new_profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error: {e} occurred. Rolling back."
        )