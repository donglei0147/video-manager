import re
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.config import ASSETS_DIR
from app.db.models import ThemeBackground, Video
from app.schemas.video import ThemeBackgroundBrief
from app.services.ffmpeg_service import FfmpegError, extract_frame
from app.services.ffprobe_service import probe_video
from app.utils import now_local_str

AUTO_NAME_RE = re.compile(r"^room_(\d+)$", re.IGNORECASE)
THEME_NAME_RE = re.compile(r"^[\u4e00-\u9fff_a-zA-Z0-9_-]+$")


def theme_image_url(background_id: int) -> str:
    return f"/api/theme-backgrounds/{background_id}/image"


def _asset_path(background_id: int) -> Path:
    return ASSETS_DIR / f"{background_id}.jpg"


def _validate_name(name: str) -> str:
    trimmed = name.strip()
    if not trimmed:
        raise api_error(400, "VALIDATION_ERROR", "名称不能为空")
    if len(trimmed) > 64:
        raise api_error(400, "VALIDATION_ERROR", "名称长度不能超过 64")
    if not THEME_NAME_RE.match(trimmed):
        raise api_error(
            400,
            "VALIDATION_ERROR",
            "名称仅允许中文、字母、数字、下划线与连字符",
        )
    return trimmed


def next_auto_name(db: Session) -> str:
    rows = db.scalars(select(ThemeBackground.name)).all()
    max_num = 0
    for name in rows:
        match = AUTO_NAME_RE.match(name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"room_{max_num + 1:04d}"


def resolve_name(db: Session, name: str | None) -> str:
    if name is None or not name.strip():
        return next_auto_name(db)
    resolved = _validate_name(name)
    existing = db.scalar(select(ThemeBackground).where(ThemeBackground.name == resolved))
    if existing:
        raise api_error(409, "CONFLICT", "主题背景图名称已存在")
    return resolved


def video_count_for(db: Session, background_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Video)
            .where(Video.theme_background_id == background_id)
        )
        or 0
    )


def theme_background_out(db: Session, bg: ThemeBackground) -> dict:
    return {
        "id": bg.id,
        "name": bg.name,
        "image_url": theme_image_url(bg.id),
        "source_video_id": bg.source_video_id,
        "source_time_sec": bg.source_time_sec,
        "width": bg.width,
        "height": bg.height,
        "video_count": video_count_for(db, bg.id),
        "created_at": bg.created_at,
        "updated_at": bg.updated_at,
    }


def theme_background_brief(bg: ThemeBackground) -> dict:
    return {
        "id": bg.id,
        "name": bg.name,
        "image_url": theme_image_url(bg.id),
    }


def _theme_for_video(db: Session, theme_background_id: int | None) -> ThemeBackgroundBrief | None:
    if theme_background_id is None:
        return None
    bg = db.get(ThemeBackground, theme_background_id)
    if bg is None:
        return None
    return ThemeBackgroundBrief(
        id=bg.id,
        name=bg.name,
        image_url=theme_image_url(bg.id),
    )


def list_theme_backgrounds(
    db: Session,
    *,
    page: int,
    page_size: int,
    keyword: str | None = None,
) -> tuple[list[dict], int]:
    filters = []
    if keyword:
        kw = f"%{keyword.strip()}%"
        filters.append(ThemeBackground.name.like(kw))

    count_stmt = select(func.count()).select_from(ThemeBackground)
    stmt = select(ThemeBackground)
    for f in filters:
        count_stmt = count_stmt.where(f)
        stmt = stmt.where(f)

    total = db.scalar(count_stmt) or 0
    offset = (page - 1) * page_size
    rows = db.scalars(
        stmt.order_by(ThemeBackground.id.desc()).offset(offset).limit(page_size)
    ).all()
    return [theme_background_out(db, bg) for bg in rows], total


def create_from_frame(
    db: Session,
    video: Video,
    *,
    time_sec: float,
    name: str | None,
) -> ThemeBackground:
    if video.missing:
        raise api_error(404, "FILE_NOT_FOUND", "视频文件不存在或已缺失")
    source_path = Path(video.file_path)
    if not source_path.is_file():
        raise api_error(404, "FILE_NOT_FOUND", "磁盘文件不存在")
    if video.duration_sec is not None and time_sec > video.duration_sec:
        raise api_error(400, "VALIDATION_ERROR", "截帧时间超出视频时长")
    if video.theme_background_id is not None:
        raise api_error(409, "CONFLICT", "视频已关联主题背景图，请通过下拉修改")

    resolved_name = resolve_name(db, name)
    now = now_local_str()
    bg = ThemeBackground(
        name=resolved_name,
        file_path="",
        source_video_id=video.id,
        source_time_sec=time_sec,
        width=None,
        height=None,
        created_at=now,
        updated_at=now,
    )
    db.add(bg)
    db.flush()

    output_path = _asset_path(bg.id)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        extract_frame(str(source_path), output_path, time_sec)
    except FfmpegError as exc:
        db.rollback()
        raise api_error(500, "INTERNAL_ERROR", f"截帧失败: {exc}") from exc

    probe = probe_video(str(output_path))
    bg.file_path = str(output_path)
    bg.width = probe.width if probe else video.width
    bg.height = probe.height if probe else video.height
    video.theme_background_id = bg.id
    video.updated_at = now_local_str()
    db.commit()
    db.refresh(bg)
    return bg


def link_theme_background(db: Session, video: Video, background_id: int) -> Video:
    bg = db.get(ThemeBackground, background_id)
    if bg is None:
        raise api_error(404, "NOT_FOUND", "主题背景图不存在")
    if not Path(bg.file_path).is_file():
        raise api_error(404, "FILE_NOT_FOUND", "主题背景图文件不存在")
    video.theme_background_id = bg.id
    video.updated_at = now_local_str()
    db.commit()
    db.refresh(video)
    return video


def unlink_theme_background(db: Session, video: Video) -> None:
    video.theme_background_id = None
    video.updated_at = now_local_str()
    db.commit()


def rename_theme_background(db: Session, bg: ThemeBackground, name: str) -> ThemeBackground:
    resolved = _validate_name(name)
    dup = db.scalar(
        select(ThemeBackground).where(
            ThemeBackground.name == resolved, ThemeBackground.id != bg.id
        )
    )
    if dup:
        raise api_error(409, "CONFLICT", "主题背景图名称已存在")
    bg.name = resolved
    bg.updated_at = now_local_str()
    db.commit()
    db.refresh(bg)
    return bg


def delete_theme_background(db: Session, bg: ThemeBackground) -> None:
    videos = db.scalars(
        select(Video).where(Video.theme_background_id == bg.id)
    ).all()
    for video in videos:
        video.theme_background_id = None
        video.updated_at = now_local_str()

    file_path = Path(bg.file_path)
    if file_path.is_file():
        try:
            file_path.unlink()
        except OSError as exc:
            raise api_error(500, "INTERNAL_ERROR", f"删除图片失败: {exc}") from exc

    db.delete(bg)
    db.commit()
