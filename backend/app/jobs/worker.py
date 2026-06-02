import logging
import threading

from sqlalchemy import func, select

from app.config import settings
from app.db.models import Job
from app.db.session import SessionLocal
from app.services.ffmpeg_service import FfmpegError
from app.services.job_service import execute_merge_videos_job, execute_video_clip_job
from app.utils import now_local_str

logger = logging.getLogger(__name__)

_wake = threading.Event()
_thread: threading.Thread | None = None
_stop = threading.Event()


def notify_job_queued() -> None:
    _wake.set()


def _run_job(db, job: Job) -> None:
    now = now_local_str()
    job.status = "running"
    job.started_at = now
    job.error = None
    db.commit()

    try:
        if job.type == "video_clip":
            execute_video_clip_job(db, job)
        elif job.type == "merge_videos":
            execute_merge_videos_job(db, job)
        else:
            raise FfmpegError(f"未知任务类型: {job.type}")

        job.status = "success"
        job.finished_at = now_local_str()
        db.commit()
    except FfmpegError as exc:
        db.rollback()
        job = db.get(Job, job.id)
        if job:
            job.status = "failed"
            job.error = str(exc)
            job.finished_at = now_local_str()
            db.commit()
    except Exception:
        logger.exception("Job %s failed", job.id)
        db.rollback()
        job = db.get(Job, job.id)
        if job:
            job.status = "failed"
            job.error = "任务执行异常"
            job.finished_at = now_local_str()
            db.commit()


def _worker_loop() -> None:
    while not _stop.is_set():
        _wake.wait(timeout=1.0)
        _wake.clear()
        if _stop.is_set():
            break

        db = SessionLocal()
        try:
            running = db.scalar(
                select(func.count()).select_from(Job).where(Job.status == "running")
            ) or 0
            if running >= settings.job_concurrency:
                continue

            job = db.scalar(
                select(Job).where(Job.status == "queued").order_by(Job.id).limit(1)
            )
            if job is None:
                continue

            _run_job(db, job)
        finally:
            db.close()


def start_worker() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_worker_loop, name="job-worker", daemon=True)
    _thread.start()
    logger.info("Job worker started (concurrency=%s)", settings.job_concurrency)


def stop_worker() -> None:
    _stop.set()
    _wake.set()
    if _thread is not None:
        _thread.join(timeout=5.0)
