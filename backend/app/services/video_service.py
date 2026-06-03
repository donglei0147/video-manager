import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import Category, JobVideo, Tag, Video, VideoTag
from app.schemas.video import CategoryBrief, TagBrief, VideoSummary
from app.services.theme_background_service import _theme_for_video
from app.utils import is_valid_datetime, now_local_str, playback_supported


@dataclass
class VideoListFilters:
    category_id: int | None = None
    tag_ids: list[int] | None = None
    q: str | None = None
    record_start_from: str | None = None
    record_start_to: str | None = None
    record_end_from: str | None = None
    record_end_to: str | None = None
    has_record_time: bool | None = None
    favorite_min: int | None = None
    theme_background_id: int | None = None
    include_missing: bool = False


def _tags_for_video(db: Session, video_id: int) -> list[TagBrief]:
    rows = db.execute(
        select(Tag.id, Tag.name)
        .join(VideoTag, VideoTag.tag_id == Tag.id)
        .where(VideoTag.video_id == video_id)
    ).all()
    return [TagBrief(id=r[0], name=r[1]) for r in rows]


def _category_for_video(db: Session, category_id: int | None) -> CategoryBrief | None:
    if category_id is None:
        return None
    cat = db.get(Category, category_id)
    if cat is None:
        return None
    return CategoryBrief(id=cat.id, name=cat.name)


def video_to_summary(db: Session, v: Video) -> VideoSummary:
    return VideoSummary(
        id=v.id,
        file_name=v.file_name,
        ext=v.ext,
        file_size=v.file_size,
        duration_sec=v.duration_sec,
        width=v.width,
        height=v.height,
        record_start_at=v.record_start_at,
        record_end_at=v.record_end_at,
        favorite_level=v.favorite_level,
        file_mtime=v.file_mtime,
        metadata_status=v.metadata_status,
        missing=bool(v.missing),
        playback_supported=playback_supported(
            v.video_codec, v.audio_codec, v.metadata_status, bool(v.missing)
        ),
        has_audio=bool(v.has_audio),
        category=_category_for_video(db, v.category_id),
        tags=_tags_for_video(db, v.id),
        theme_background=_theme_for_video(db, v.theme_background_id),
        stream_url=f"/api/videos/{v.id}/stream",
    )


def _apply_filters(stmt, filters: VideoListFilters):
    if not filters.include_missing:
        stmt = stmt.where(Video.missing == 0)
    if filters.category_id is not None:
        stmt = stmt.where(Video.category_id == filters.category_id)
    if filters.tag_ids:
        for tag_id in filters.tag_ids:
            stmt = stmt.where(
                Video.id.in_(
                    select(VideoTag.video_id).where(VideoTag.tag_id == tag_id)
                )
            )
    if filters.q:
        kw = f"%{filters.q}%"
        stmt = stmt.where(or_(Video.file_name.like(kw), Video.file_path.like(kw)))
    if filters.record_start_from is not None:
        stmt = stmt.where(
            Video.record_start_at.isnot(None),
            Video.record_start_at >= filters.record_start_from,
        )
    if filters.record_start_to is not None:
        stmt = stmt.where(
            Video.record_start_at.isnot(None),
            Video.record_start_at <= filters.record_start_to,
        )
    if filters.record_end_from is not None:
        stmt = stmt.where(
            Video.record_end_at.isnot(None),
            Video.record_end_at >= filters.record_end_from,
        )
    if filters.record_end_to is not None:
        stmt = stmt.where(
            Video.record_end_at.isnot(None),
            Video.record_end_at <= filters.record_end_to,
        )
    if filters.has_record_time is True:
        stmt = stmt.where(
            or_(Video.record_start_at.isnot(None), Video.record_end_at.isnot(None))
        )
    elif filters.has_record_time is False:
        stmt = stmt.where(
            and_(Video.record_start_at.is_(None), Video.record_end_at.is_(None))
        )
    if filters.favorite_min is not None:
        stmt = stmt.where(Video.favorite_level >= filters.favorite_min)
    if filters.theme_background_id is not None:
        stmt = stmt.where(Video.theme_background_id == filters.theme_background_id)
    return stmt


def _apply_sort(stmt, sort: str):
    if sort == "file_mtime_asc":
        return stmt.order_by(Video.file_mtime.asc().nullslast())
    if sort == "favorite_desc":
        return stmt.order_by(
            Video.favorite_level.desc(), Video.file_mtime.desc().nullslast()
        )
    if sort == "favorite_asc":
        return stmt.order_by(
            Video.favorite_level.asc(), Video.file_mtime.desc().nullslast()
        )
    if sort == "record_start_desc":
        return stmt.order_by(Video.record_start_at.desc().nullslast())
    if sort == "record_start_asc":
        return stmt.order_by(Video.record_start_at.asc().nullslast())
    return stmt.order_by(Video.file_mtime.desc().nullslast())


def list_videos(
    db: Session,
    *,
    page: int,
    page_size: int,
    filters: VideoListFilters,
    sort: str = "file_mtime_desc",
) -> tuple[list[VideoSummary], int]:
    base = select(Video)
    base = _apply_filters(base, filters)
    base = _apply_sort(base, sort)

    count_stmt = select(func.count()).select_from(Video)
    count_stmt = _apply_filters(count_stmt, filters)
    total = db.scalar(count_stmt) or 0

    offset = (page - 1) * page_size
    rows = db.scalars(base.offset(offset).limit(page_size)).all()
    items = [video_to_summary(db, v) for v in rows]
    return items, total


def update_video(db: Session, video: Video, updates: dict) -> Video:
    if "category_id" in updates:
        category_id = updates["category_id"]
        if category_id is not None:
            cat = db.get(Category, category_id)
            if cat is None:
                raise api_error(400, "VALIDATION_ERROR", "分类不存在")
        video.category_id = category_id

    if "tag_ids" in updates:
        tag_ids = updates["tag_ids"] or []
        for tid in tag_ids:
            if db.get(Tag, tid) is None:
                raise api_error(400, "VALIDATION_ERROR", f"标签 {tid} 不存在")
        db.execute(
            VideoTag.__table__.delete().where(VideoTag.video_id == video.id)
        )
        for tid in tag_ids:
            db.add(VideoTag(video_id=video.id, tag_id=tid))

    if "record_start_at" in updates:
        record_start_at = updates["record_start_at"]
        if record_start_at is not None and not is_valid_datetime(record_start_at):
            raise api_error(400, "VALIDATION_ERROR", "record_start_at 格式须为 YYYY-MM-DD HH:MM:SS")
        video.record_start_at = record_start_at

    if "record_end_at" in updates:
        record_end_at = updates["record_end_at"]
        if record_end_at is not None and not is_valid_datetime(record_end_at):
            raise api_error(400, "VALIDATION_ERROR", "record_end_at 格式须为 YYYY-MM-DD HH:MM:SS")
        video.record_end_at = record_end_at

    if (
        video.record_start_at
        and video.record_end_at
        and video.record_end_at < video.record_start_at
    ):
        raise api_error(400, "VALIDATION_ERROR", "录制结束时间不能早于开始时间")

    if "favorite_level" in updates:
        favorite_level = updates["favorite_level"]
        if favorite_level is None or favorite_level < 0 or favorite_level > 10:
            raise api_error(400, "VALIDATION_ERROR", "favorite_level 须在 0～10")
        video.favorite_level = favorite_level

    video.updated_at = now_local_str()
    db.commit()
    db.refresh(video)
    return video


def delete_video_to_delete_dir(db: Session, video: Video) -> None:
    source_path = Path(video.file_path)
    if not source_path.is_file():
        raise api_error(404, "FILE_NOT_FOUND", "视频文件不存在或已缺失")

    delete_dir = source_path.parent / "_delete"
    delete_dir.mkdir(parents=True, exist_ok=True)
    target_path = delete_dir / source_path.name

    try:
        if target_path.exists():
            target_path.unlink()
        shutil.move(str(source_path), str(target_path))
    except OSError as exc:
        raise api_error(500, "INTERNAL_ERROR", f"移动到 _delete 失败: {exc}") from exc

    db.execute(VideoTag.__table__.delete().where(VideoTag.video_id == video.id))
    db.execute(JobVideo.__table__.delete().where(JobVideo.video_id == video.id))
    db.delete(video)
    db.commit()
