from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import alerts, auth, eval as eval_api, investigations, stats
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.seed import seed_if_empty

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins + ["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(investigations.router)
app.include_router(stats.router)
app.include_router(eval_api.router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_enabled": bool(settings.openai_api_key),
        "demo_mode": settings.demo_mode,
    }


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
