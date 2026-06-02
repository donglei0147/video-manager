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
