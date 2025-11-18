from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.common.db import init_db
from src.auth.routes import auth_router
from src.onboarding.routes import profile_router
from src.dashboard.routes import dashboard_router
from src.lessons.routes import lessons_router

app = FastAPI(
    title="Briefly API"
)

@app.on_event("startup")
def startup():
    init_db()

print(app)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(auth_router)
app.include_router(profile_router)
app.include_router(dashboard_router)
app.include_router(lessons_router)

@app.get("/")
def root():
    return {
        "hello": "world"
    }

