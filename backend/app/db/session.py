import sqlite3
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATA_DIR, settings

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.close()


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_scan_folder_error_column() -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info(scan_folder)")).fetchall()
        names = {row[1] for row in rows}
        if "last_scan_error" not in names:
            conn.execute(text("ALTER TABLE scan_folder ADD COLUMN last_scan_error TEXT"))
            conn.commit()


def _migrate_theme_background() -> None:
    with engine.connect() as conn:
        tables = {
            row[0]
            for row in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
        }
        if "theme_background" not in tables:
            conn.execute(
                text(
                    """
                    CREATE TABLE theme_background (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        file_path TEXT NOT NULL UNIQUE,
                        source_video_id INTEGER,
                        source_time_sec REAL,
                        width INTEGER,
                        height INTEGER,
                        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
                        updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
                    )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_theme_background_name ON theme_background(name)"
                )
            )
            conn.commit()

        rows = conn.execute(text("PRAGMA table_info(video)")).fetchall()
        names = {row[1] for row in rows}
        if "theme_background_id" not in names:
            conn.execute(text("ALTER TABLE video ADD COLUMN theme_background_id INTEGER"))
            conn.commit()
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_video_theme_background ON video(theme_background_id)"
            )
        )
        conn.commit()


def init_db() -> None:
    sql_path = Path(__file__).resolve().parents[2] / "scripts" / "init_db.sql"
    script = sql_path.read_text(encoding="utf-8")
    raw = engine.raw_connection()
    try:
        raw.executescript(script)
        raw.commit()
    finally:
        raw.close()
    _migrate_scan_folder_error_column()
    _migrate_theme_background()
