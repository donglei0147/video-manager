from sqlalchemy import BigInteger, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ScanFolder(Base):
    __tablename__ = "scan_folder"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_scan_at: Mapped[str | None] = mapped_column(String, nullable=True)
    last_scan_status: Mapped[str] = mapped_column(String, nullable=False, default="idle")
    last_scan_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Video(Base):
    __tablename__ = "video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_folder_id: Mapped[int] = mapped_column(Integer, nullable=False)
    file_path: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    ext: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    video_codec: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_codec: Mapped[str | None] = mapped_column(String, nullable=True)
    has_audio: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    record_start_at: Mapped[str | None] = mapped_column(String, nullable=True)
    record_end_at: Mapped[str | None] = mapped_column(String, nullable=True)
    favorite_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_mtime: Mapped[str | None] = mapped_column(String, nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    missing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    indexed_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Tag(Base):
    __tablename__ = "tag"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class VideoTag(Base):
    __tablename__ = "video_tag"

    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Job(Base):
    __tablename__ = "job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[str | None] = mapped_column(String, nullable=True)
    finished_at: Mapped[str | None] = mapped_column(String, nullable=True)


class JobVideo(Base):
    __tablename__ = "job_video"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
