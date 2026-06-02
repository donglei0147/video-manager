import shutil
import subprocess

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import SessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    db_ok = False
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_ok = True
    except Exception:
        db_ok = False

    ffmpeg_ok = shutil.which(settings.ffmpeg_path) is not None

    return {
        "status": "ok" if db_ok else "degraded",
        "ffmpeg_available": ffmpeg_ok,
        "db_available": db_ok,
    }
