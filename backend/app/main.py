import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS
from app.database import get_db
from app.routers.auth import router as auth_router
from app.routers.categories import router as categories_router
from app.services.auth import cleanup_expired_sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(cleanup_expired_sessions())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="TextGenie API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(categories_router)


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "message": "TextGenie API is running"}
