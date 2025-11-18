from fastapi import (
    APIRouter,
    Depends,
    status,
    HTTPException,
    Request
)

from src.common.config import settings, templates

dashboard_router = APIRouter(
    tags=["DASHBOARD"],
    prefix="/dashboard"
)

@dashboard_router.get("/")
def get_dashboard(request: Request):
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error: {e} occurred"
        )