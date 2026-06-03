from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.core.config import get_settings
from backend.core.logging import configure_logging
from backend.db.seed import ensure_default_profile
from backend.db.session import SessionLocal, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    db = SessionLocal()
    try:
        ensure_default_profile(db)
    finally:
        db.close()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

