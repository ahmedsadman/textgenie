import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import CORS_ORIGINS
from app.database import get_db
from app.logging_config import configure_logging
from app.routers.auth import router as auth_router
from app.routers.banks import router as banks_router
from app.routers.bills import router as bills_router
from app.routers.categories import router as categories_router
from app.routers.messages import router as messages_router
from app.routers.settings import router as settings_router
from app.routers.transactions import router as transactions_router
from app.routers.webhook import router as webhook_router
from app.services.auth import cleanup_expired_sessions

configure_logging()


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
app.include_router(banks_router)
app.include_router(bills_router)
app.include_router(categories_router)
app.include_router(messages_router)
app.include_router(settings_router)
app.include_router(transactions_router)
app.include_router(webhook_router)


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "message": "TextGenie API is running"}
