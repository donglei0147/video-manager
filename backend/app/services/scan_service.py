import os
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ScanFolder, Video
from app.services import ffprobe_service, scan_state
from app.utils import format_mtime, is_video_ext, now_local_str, normalize_path


def _walk_skip_permission(err: OSError) -> None:
    """Skip unreadable directories on Windows instead of aborting the whole scan."""


def iter_video_files(root: Path):
    """Recursively yield mp4/mov files; skip _temp and _delete directories."""
    if not root.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(root, onerror=_walk_skip_permission):
        dirnames[:] = [d for d in dirnames if d.lower() not in {"_temp", "_delete"}]
        for name in filenames:
            p = Path(dirpath) / name
            if is_video_ext(p):
                yield p


def count_video_files(root: Path) -> int:
    return sum(1 for _ in iter_video_files(root))


def scan_folder_sync(db: Session, folder: ScanFolder) -> None:
    folder_id = folder.id
    root = Path(folder.path)
    if not root.exists():
        raise FileNotFoundError(f"扫描路径不存在: {folder.path}")
    if not root.is_dir():
        raise NotADirectoryError(f"扫描路径不是文件夹: {folder.path}")

    prog = scan_state.FolderScanProgress(phase="fast")
    scan_state.set_progress(folder_id, prog)

    folder.last_scan_status = "scanning"
    folder.last_scan_error = None
    db.commit()

    disk_files: dict[str, tuple[int, str]] = {}
    total = 0
    for fp in iter_video_files(root):
        total += 1
        try:
            st = fp.stat()
            disk_files[normalize_path(str(fp))] = (st.st_size, format_mtime(st.st_mtime))
        except OSError:
            continue

    prog.fast_total = total
    scan_state.set_progress(folder_id, prog)

    existing_rows = db.scalars(
        select(Video).where(Video.scan_folder_id == folder_id)
    ).all()
    existing_by_path = {normalize_path(v.file_path): v for v in existing_rows}

    processed = 0
    now = now_local_str()

    for file_path, (file_size, file_mtime) in disk_files.items():
        processed += 1
        prog.fast_processed = processed
        scan_state.set_progress(folder_id, prog)

        p = Path(file_path)
        ext = p.suffix.lower().lstrip(".")
        file_name = p.name

        row = existing_by_path.get(file_path)
        if row is None:
            row = Video(
                scan_folder_id=folder_id,
                file_path=file_path,
                file_name=file_name,
                ext=ext,
                file_size=file_size,
                file_mtime=file_mtime,
                metadata_status="pending",
                missing=0,
                indexed_at=now,
                updated_at=now,
            )
            db.add(row)
        else:
            changed = row.file_size != file_size or row.file_mtime != file_mtime
            row.missing = 0
            if changed:
                row.file_size = file_size
                row.file_mtime = file_mtime
                row.file_name = file_name
                row.ext = ext
                row.metadata_status = "pending"
                row.duration_sec = None
                row.width = None
                row.height = None
                row.video_codec = None
                row.audio_codec = None
                row.has_audio = 1
                row.updated_at = now
        db.flush()

    for file_path, row in existing_by_path.items():
        if file_path not in disk_files:
            if row.missing == 0:
                row.missing = 1
                row.updated_at = now

    db.commit()

    _run_metadata_phase(db, folder_id, prog)

    count = db.scalar(
        select(func.count()).select_from(Video).where(
            Video.scan_folder_id == folder_id, Video.missing == 0
        )
    )
    folder = db.get(ScanFolder, folder_id)
    if folder:
        folder.video_count = count or 0
        folder.last_scan_at = now_local_str()
        folder.last_scan_status = "success"
        folder.last_scan_error = None
    prog.phase = "idle"
    prog.last_error = None
    scan_state.set_progress(folder_id, prog)
    db.commit()


def run_metadata_only(
    db: Session, folder_id: int, prog: scan_state.FolderScanProgress
) -> None:
    """Re-probe videos with pending or failed metadata (no filesystem walk)."""
    stale = db.scalars(
        select(Video).where(
            Video.scan_folder_id == folder_id,
            Video.missing == 0,
            Video.metadata_status == "failed",
        )
    ).all()
    for row in stale:
        row.metadata_status = "pending"
    if stale:
        db.commit()
    _run_metadata_phase(db, folder_id, prog)


def _run_metadata_phase(db: Session, folder_id: int, prog: scan_state.FolderScanProgress) -> None:
    pending = db.scalars(
        select(Video).where(
            Video.scan_folder_id == folder_id,
            Video.metadata_status == "pending",
            Video.missing == 0,
        )
    ).all()

    prog.phase = "metadata"
    prog.metadata_total = len(pending)
    prog.metadata_processed = 0
    prog.metadata_failed = 0
    scan_state.set_progress(folder_id, prog)

    now = now_local_str()
    for row in pending:
        prog.metadata_processed += 1
        scan_state.set_progress(folder_id, prog)

        file_path = Path(row.file_path)
        if not file_path.is_file():
            row.metadata_status = "failed"
            prog.metadata_failed += 1
            row.updated_at = now
            continue

        result = ffprobe_service.probe_video(str(file_path))
        if result is None:
            row.metadata_status = "failed"
            prog.metadata_failed += 1
            row.updated_at = now
            continue

        row.duration_sec = result.duration_sec
        row.width = result.width
        row.height = result.height
        row.video_codec = result.video_codec
        row.audio_codec = result.audio_codec if result.has_audio else None
        row.has_audio = 1 if result.has_audio else 0
        row.metadata_status = "ready"
        row.updated_at = now

    db.commit()


def is_scanning(folder: ScanFolder) -> bool:
    return folder.last_scan_status == "scanning"
