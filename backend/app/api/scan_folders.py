import logging
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import ScanFolder, Video
from app.db.session import get_db
from app.schemas.scan_folder import (
    ScanFolderCreate,
    ScanFolderListResponse,
    ScanFolderOut,
    ScanFolderUpdate,
    ScanStartResponse,
    ScanStatusResponse,
)
from app.services import scan_service, scan_state
from app.utils import normalize_path, now_local_str

router = APIRouter(prefix="/scan-folders", tags=["scan-folders"])
logger = logging.getLogger(__name__)

_scan_lock = threading.Lock()
_active_scans: set[int] = set()

_MAX_ERROR_LEN = 2000


def _truncate_error(msg: str) -> str:
    if len(msg) <= _MAX_ERROR_LEN:
        return msg
    return msg[: _MAX_ERROR_LEN - 3] + "..."


def _live_video_count(db: Session, folder_id: int) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Video)
            .where(Video.scan_folder_id == folder_id, Video.missing == 0)
        )
        or 0
    )


def _to_out(folder: ScanFolder, db: Session) -> ScanFolderOut:
    count = _live_video_count(db, folder.id)
    if count != folder.video_count:
        folder.video_count = count
    return ScanFolderOut(
        id=folder.id,
        path=folder.path,
        enabled=bool(folder.enabled),
        last_scan_at=folder.last_scan_at,
        last_scan_status=folder.last_scan_status,
        last_scan_error=folder.last_scan_error,
        video_count=count,
        created_at=folder.created_at,
    )


def _run_scan_background(folder_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        folder = db.get(ScanFolder, folder_id)
        if folder is None:
            return
        scan_service.scan_folder_sync(db, folder)
    except Exception as exc:
        err_msg = _truncate_error(f"{type(exc).__name__}: {exc}")
        logger.exception("Scan failed for folder_id=%s", folder_id)
        folder = db.get(ScanFolder, folder_id)
        if folder:
            folder.last_scan_status = "failed"
            folder.last_scan_error = err_msg
            folder.video_count = _live_video_count(db, folder_id)
            db.commit()
        prog = scan_state.get_progress(folder_id)
        prog.phase = "idle"
        prog.last_error = err_msg
        scan_state.set_progress(folder_id, prog)
    finally:
        with _scan_lock:
            _active_scans.discard(folder_id)
        db.close()


@router.get("", response_model=ScanFolderListResponse)
def list_scan_folders(db: Session = Depends(get_db)):
    folders = db.scalars(select(ScanFolder).order_by(ScanFolder.id)).all()
    items = [_to_out(f, db) for f in folders]
    db.commit()
    return ScanFolderListResponse(items=items)


@router.post("", response_model=ScanFolderOut, status_code=201)
def create_scan_folder(body: ScanFolderCreate, db: Session = Depends(get_db)):
    path = normalize_path(body.path)
    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise api_error(400, "VALIDATION_ERROR", "路径不存在或不是文件夹")
    existing = db.scalar(select(ScanFolder).where(ScanFolder.path == path))
    if existing:
        raise api_error(409, "CONFLICT", "该扫描文件夹已存在")

    folder = ScanFolder(
        path=path,
        enabled=1,
        last_scan_status="idle",
        video_count=0,
        created_at=now_local_str(),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return _to_out(folder, db)


@router.patch("/{folder_id}", response_model=ScanFolderOut)
def update_scan_folder(
    folder_id: int, body: ScanFolderUpdate, db: Session = Depends(get_db)
):
    folder = db.get(ScanFolder, folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "扫描文件夹不存在")
    if body.enabled is not None:
        folder.enabled = 1 if body.enabled else 0
    db.commit()
    db.refresh(folder)
    return _to_out(folder, db)


@router.delete("/{folder_id}", status_code=204)
def delete_scan_folder(
    folder_id: int,
    delete_videos: bool = Query(False),
    db: Session = Depends(get_db),
):
    folder = db.get(ScanFolder, folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "扫描文件夹不存在")

    if delete_videos:
        from app.db.models import VideoTag

        video_ids = list(
            db.scalars(
                select(Video.id).where(Video.scan_folder_id == folder_id)
            ).all()
        )
        if video_ids:
            db.execute(delete(VideoTag).where(VideoTag.video_id.in_(video_ids)))
            db.execute(delete(Video).where(Video.id.in_(video_ids)))

    db.delete(folder)
    db.commit()
    return Response(status_code=204)


def _run_metadata_background(folder_id: int) -> None:
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        folder = db.get(ScanFolder, folder_id)
        if folder is None:
            return
        prog = scan_state.FolderScanProgress(phase="metadata")
        scan_state.set_progress(folder_id, prog)
        folder.last_scan_status = "scanning"
        folder.last_scan_error = None
        db.commit()
        scan_service.run_metadata_only(db, folder_id, prog)
        folder = db.get(ScanFolder, folder_id)
        if folder:
            folder.video_count = _live_video_count(db, folder_id)
            folder.last_scan_at = now_local_str()
            folder.last_scan_status = "success"
            folder.last_scan_error = None
            prog.phase = "idle"
            prog.last_error = None
            scan_state.set_progress(folder_id, prog)
            db.commit()
    except Exception as exc:
        err_msg = _truncate_error(f"{type(exc).__name__}: {exc}")
        logger.exception("Metadata resync failed for folder_id=%s", folder_id)
        folder = db.get(ScanFolder, folder_id)
        if folder:
            folder.last_scan_status = "failed"
            folder.last_scan_error = err_msg
            folder.video_count = _live_video_count(db, folder_id)
            db.commit()
        prog = scan_state.get_progress(folder_id)
        prog.phase = "idle"
        prog.last_error = err_msg
        scan_state.set_progress(folder_id, prog)
    finally:
        with _scan_lock:
            _active_scans.discard(folder_id)
        db.close()


@router.post("/{folder_id}/resync-metadata", response_model=ScanStartResponse, status_code=202)
def resync_metadata(folder_id: int, db: Session = Depends(get_db)):
    """补全/重试该文件夹内 pending 或 failed 的 ffprobe 元数据。"""
    folder = db.get(ScanFolder, folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "扫描文件夹不存在")
    if not folder.enabled:
        raise api_error(400, "VALIDATION_ERROR", "该文件夹已停用")

    with _scan_lock:
        if folder_id in _active_scans:
            raise api_error(409, "SCAN_IN_PROGRESS", "该文件夹正在扫描")
        _active_scans.add(folder_id)

    thread = threading.Thread(target=_run_metadata_background, args=(folder_id,), daemon=True)
    thread.start()
    return ScanStartResponse(
        scan_folder_id=folder_id,
        status="scanning",
        phase="metadata",
        processed=0,
        total=0,
    )


@router.post("/{folder_id}/scan", response_model=ScanStartResponse, status_code=202)
def scan_one_folder(folder_id: int, db: Session = Depends(get_db)):
    folder = db.get(ScanFolder, folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "扫描文件夹不存在")
    if not folder.enabled:
        raise api_error(400, "VALIDATION_ERROR", "该文件夹已停用")

    with _scan_lock:
        if folder_id in _active_scans:
            raise api_error(409, "SCAN_IN_PROGRESS", "该文件夹正在扫描")
        _active_scans.add(folder_id)

    folder.last_scan_status = "scanning"
    folder.last_scan_error = None
    db.commit()

    thread = threading.Thread(target=_run_scan_background, args=(folder_id,), daemon=True)
    thread.start()

    return ScanStartResponse(
        scan_folder_id=folder_id,
        status="scanning",
        phase="fast",
        processed=0,
        total=0,
    )


@router.post("/scan-all", response_model=ScanStartResponse, status_code=202)
def scan_all_folders(db: Session = Depends(get_db)):
    folders = db.scalars(
        select(ScanFolder).where(ScanFolder.enabled == 1)
    ).all()
    if not folders:
        raise api_error(400, "VALIDATION_ERROR", "没有启用的扫描文件夹")

    def run_all():
        for f in folders:
            with _scan_lock:
                if f.id in _active_scans:
                    continue
                _active_scans.add(f.id)
            _run_scan_background(f.id)

    thread = threading.Thread(target=run_all, daemon=True)
    thread.start()

    return ScanStartResponse(
        scan_folder_id=None,
        status="scanning",
        phase="fast",
        processed=0,
        total=0,
    )


@router.get("/{folder_id}/status", response_model=ScanStatusResponse)
def scan_status(folder_id: int, db: Session = Depends(get_db)):
    folder = db.get(ScanFolder, folder_id)
    if folder is None:
        raise api_error(404, "NOT_FOUND", "扫描文件夹不存在")

    prog = scan_state.get_progress(folder_id)
    error = folder.last_scan_error or prog.last_error
    return ScanStatusResponse(
        scan_folder_id=folder_id,
        last_scan_status=folder.last_scan_status,
        phase=prog.phase if folder.last_scan_status == "scanning" else "idle",
        last_scan_error=error,
        fast_scan={"processed": prog.fast_processed, "total": prog.fast_total},
        metadata_scan={
            "processed": prog.metadata_processed,
            "total": prog.metadata_total,
            "failed": prog.metadata_failed,
        },
    )
