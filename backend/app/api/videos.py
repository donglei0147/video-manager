import re
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import ScanFolder, Video
from app.db.session import get_db
from app.schemas.common import paginate
from app.schemas.video import VideoUpdate
from app.schemas.theme_background import ThemeBackgroundFromFrame
from app.services.theme_background_service import (
    create_from_frame,
    link_theme_background,
    theme_background_out,
    unlink_theme_background,
)
from app.services.video_service import (
    VideoListFilters,
    delete_video_to_delete_dir,
    list_videos,
    update_video,
    video_to_summary,
)
from app.utils import normalize_path

router = APIRouter(prefix="/videos", tags=["videos"])

MEDIA_TYPES = {"mp4": "video/mp4", "mov": "video/quicktime"}
RANGE_RE = re.compile(r"bytes=(\d+)-(\d*)")


def _path_allowed(db: Session, file_path: str) -> bool:
    norm = normalize_path(file_path)
    folders = db.scalars(select(ScanFolder)).all()
    for folder in folders:
        root = normalize_path(folder.path)
        try:
            Path(norm).relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _video_detail_dict(db: Session, v: Video) -> dict:
    summary = video_to_summary(db, v)
    detail = summary.model_dump()
    detail.update(
        {
            "scan_folder_id": v.scan_folder_id,
            "file_path": v.file_path,
            "video_codec": v.video_codec,
            "audio_codec": v.audio_codec,
            "indexed_at": v.indexed_at,
            "updated_at": v.updated_at,
        }
    )
    return detail


def _parse_tag_ids(tag_ids: str | None) -> list[int] | None:
    if not tag_ids:
        return None
    try:
        return [int(x.strip()) for x in tag_ids.split(",") if x.strip()]
    except ValueError:
        raise api_error(400, "VALIDATION_ERROR", "tag_ids 格式无效")


@router.get("")
def get_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    include_missing: bool = Query(False),
    sort: str = Query("file_mtime_desc"),
    category_id: int | None = Query(None),
    tag_ids: str | None = Query(None),
    q: str | None = Query(None),
    record_start_from: str | None = Query(None),
    record_start_to: str | None = Query(None),
    record_end_from: str | None = Query(None),
    record_end_to: str | None = Query(None),
    has_record_time: bool | None = Query(None),
    favorite_min: int | None = Query(None, ge=1, le=10),
    theme_background_id: int | None = Query(None),
    db: Session = Depends(get_db),
):
    filters = VideoListFilters(
        category_id=category_id,
        tag_ids=_parse_tag_ids(tag_ids),
        q=q,
        record_start_from=record_start_from,
        record_start_to=record_start_to,
        record_end_from=record_end_from,
        record_end_to=record_end_to,
        has_record_time=has_record_time,
        favorite_min=favorite_min,
        theme_background_id=theme_background_id,
        include_missing=include_missing,
    )
    items, total = list_videos(
        db,
        page=page,
        page_size=page_size,
        filters=filters,
        sort=sort,
    )
    return paginate([i.model_dump() for i in items], page, page_size, total)


@router.get("/{video_id}")
def get_video(video_id: int, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    return _video_detail_dict(db, v)


@router.patch("/{video_id}")
def patch_video(video_id: int, body: VideoUpdate, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return _video_detail_dict(db, v)
    v = update_video(db, v, updates)
    return _video_detail_dict(db, v)


@router.delete("/{video_id}", status_code=204)
def delete_video(video_id: int, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    delete_video_to_delete_dir(db, v)
    return Response(status_code=204)


@router.post("/{video_id}/theme-backgrounds/from-frame", status_code=201)
def create_theme_background_from_frame(
    video_id: int,
    body: ThemeBackgroundFromFrame,
    db: Session = Depends(get_db),
):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    bg = create_from_frame(db, v, time_sec=body.time_sec, name=body.name)
    return theme_background_out(db, bg)


@router.post("/{video_id}/theme-backgrounds/{background_id}/link")
def link_video_theme_background(
    video_id: int,
    background_id: int,
    db: Session = Depends(get_db),
):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    v = link_theme_background(db, v, background_id)
    return _video_detail_dict(db, v)


@router.delete("/{video_id}/theme-background", status_code=204)
def unlink_video_theme_background(video_id: int, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    unlink_theme_background(db, v)
    return Response(status_code=204)


@router.post("/{video_id}/open-folder", status_code=204)
def open_video_folder(video_id: int, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None:
        raise api_error(404, "NOT_FOUND", "视频不存在")
    if v.missing:
        raise api_error(404, "FILE_NOT_FOUND", "视频文件不存在或已缺失")
    file_path = Path(v.file_path)
    if not file_path.is_file():
        raise api_error(404, "FILE_NOT_FOUND", "磁盘文件不存在")
    try:
        subprocess.run(
            ["explorer", "/select,", str(file_path)],
            check=False,
        )
    except OSError as e:
        raise api_error(500, "INTERNAL_ERROR", f"无法打开资源管理器: {e}")
    return Response(status_code=204)


@router.get("/{video_id}/stream")
def stream_video(video_id: int, request: Request, db: Session = Depends(get_db)):
    v = db.get(Video, video_id)
    if v is None or v.missing:
        raise api_error(404, "FILE_NOT_FOUND", "视频文件不存在或已缺失")

    file_path = Path(v.file_path)
    if not file_path.is_file():
        raise api_error(404, "FILE_NOT_FOUND", "磁盘文件不存在")

    if not _path_allowed(db, v.file_path):
        raise api_error(403, "PATH_NOT_ALLOWED", "路径不在允许的扫描目录内")

    media_type = MEDIA_TYPES.get(v.ext.lower(), "application/octet-stream")
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        match = RANGE_RE.match(range_header.strip())
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else file_size - 1
            end = min(end, file_size - 1)
            if start <= end and start < file_size:
                length = end - start + 1

                def iter_range():
                    with open(file_path, "rb") as f:
                        f.seek(start)
                        remaining = length
                        while remaining > 0:
                            chunk = f.read(min(65536, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk

                return StreamingResponse(
                    iter_range(),
                    status_code=206,
                    media_type=media_type,
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Accept-Ranges": "bytes",
                        "Content-Length": str(length),
                    },
                )

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=v.file_name,
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )
