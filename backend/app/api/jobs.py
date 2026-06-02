from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.session import get_db
from app.jobs.worker import notify_job_queued
from app.schemas.job import (
    JobDetail,
    JobListResponse,
    MergePreflightRequest,
    MergePreflightResponse,
    MergeVideosRequest,
    VideoClipRequest,
    VideoClipResponse,
)
from app.services.job_service import (
    create_merge_videos_job,
    create_video_clip_job,
    job_to_dict,
    list_jobs,
    merge_preflight_check,
    retry_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/video-clip", response_model=VideoClipResponse, status_code=202)
def create_video_clip(body: VideoClipRequest, db: Session = Depends(get_db)):
    job = create_video_clip_job(db, body)
    notify_job_queued()
    return VideoClipResponse(job_id=job.id, type=job.type, status=job.status)


@router.post("/merge-videos/preflight", response_model=MergePreflightResponse)
def merge_preflight(body: MergePreflightRequest, db: Session = Depends(get_db)):
    merge_preflight_check(db, body.video_ids)
    return MergePreflightResponse(ok=True, video_ids=body.video_ids)


@router.post("/merge-videos", response_model=VideoClipResponse, status_code=202)
def create_merge_videos(body: MergeVideosRequest, db: Session = Depends(get_db)):
    job = create_merge_videos_job(db, body)
    notify_job_queued()
    return VideoClipResponse(job_id=job.id, type=job.type, status=job.status)


@router.get("", response_model=JobListResponse)
def get_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None, alias="type"),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    return list_jobs(db, page, page_size, type, status)


@router.get("/{job_id}", response_model=JobDetail)
def get_job(job_id: int, db: Session = Depends(get_db)):
    from app.db.models import Job

    job = db.get(Job, job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "任务不存在")
    return job_to_dict(db, job)


@router.post("/{job_id}/retry", response_model=VideoClipResponse, status_code=202)
def retry_failed_job(job_id: int, db: Session = Depends(get_db)):
    job = retry_job(db, job_id)
    notify_job_queued()
    return VideoClipResponse(job_id=job.id, type=job.type, status=job.status)
