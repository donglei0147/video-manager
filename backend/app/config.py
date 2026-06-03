from pathlib import Path

from pydantic_settings import BaseSettings

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = DATA_DIR / "assets" / "theme-backgrounds"


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8765
    database_url: str = f"sqlite:///{DATA_DIR / 'app.db'}"
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    job_concurrency: int = 1
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_file = ".env"


settings = Settings()
