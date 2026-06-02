import json
import shutil
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import Job, JobVideo, Video
from app.schemas.job import MergeVideosRequest, VideoClipRequest
from app.services.audio_guard import ensure_has_audio
from app.services.ffmpeg_service import (
    FfmpegError,
    clip_output_path,
    resolve_output_file_name,
    run_merge_videos,
    run_video_clip,
)
from app.utils import now_local_str


def mark_running_jobs_failed(db: Session) -> None:
    """On process restart, mark interrupted running jobs as failed."""
    now = now_local_str()
    jobs = db.scalars(select(Job).where(Job.status == "running")).all()
    for job in jobs:
        job.status = "failed"
        job.error = "进程重启导致任务中断"
        job.finished_at = now
    if jobs:
        db.commit()


def validate_clip_times(video: Video, start_sec: float, end_sec: float | None) -> None:
    if end_sec is not None:
        if end_sec <= start_sec:
            raise api_error(400, "VALIDATION_ERROR", "结束时间须大于开始时间")
        if video.duration_sec is not None and end_sec > video.duration_sec:
            raise api_error(
                400,
                "VALIDATION_ERROR",
                f"结束时间不能超过视频时长（{video.duration_sec} 秒）",
            )


def create_video_clip_job(db: Session, body: VideoClipRequest) -> Job:
    video = db.get(Video, body.video_id)
    if video is None or video.missing:
        raise api_error(404, "NOT_FOUND", "视频不存在或已缺失")
    ensure_has_audio(video)

    if not Path(video.file_path).is_file():
        raise api_error(404, "NOT_FOUND", "源视频文件不存在")

    validate_clip_times(video, body.start_sec, body.end_sec)

    try:
        output_name = resolve_output_file_name(video.file_name, video.ext, body.output_file_name)
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", str(exc)) from exc

    output = clip_output_path(video.file_path, output_name)
    payload = {
        "video_id": video.id,
        "start_sec": body.start_sec,
        "end_sec": body.end_sec,
        "output_file_name": output_name,
        "source_path": video.file_path,
        "output_path": str(output),
    }

    now = now_local_str()
    job = Job(
        type="video_clip",
        status="queued",
        payload=json.dumps(payload, ensure_ascii=False),
        output_path=str(output),
        created_at=now,
    )
    db.add(job)
    db.flush()
    db.add(JobVideo(job_id=job.id, video_id=video.id, role=0))
    db.commit()
    db.refresh(job)
    return job


def _validate_merge_videos(videos: list[Video]) -> None:
    ref = videos[0]
    for v in videos[1:]:
        if v.video_codec != ref.video_codec:
            raise api_error(
                409,
                "CODEC_MISMATCH",
                f"video_codec mismatch: {ref.video_codec} vs {v.video_codec}",
                details={
                    "video_codec": [ref.video_codec, v.video_codec],
                    "audio_codec": [ref.audio_codec, v.audio_codec],
                    "width": [ref.width, v.width],
                    "height": [ref.height, v.height],
                },
            )
        if v.audio_codec != ref.audio_codec:
            raise api_error(
                409,
                "CODEC_MISMATCH",
                f"audio_codec mismatch: {ref.audio_codec} vs {v.audio_codec}",
                details={
                    "video_codec": [ref.video_codec, v.video_codec],
                    "audio_codec": [ref.audio_codec, v.audio_codec],
                    "width": [ref.width, v.width],
                    "height": [ref.height, v.height],
                },
            )
        if v.width != ref.width or v.height != ref.height:
            raise api_error(
                409,
                "CODEC_MISMATCH",
                "分辨率不一致",
                details={
                    "video_codec": [ref.video_codec, v.video_codec],
                    "audio_codec": [ref.audio_codec, v.audio_codec],
                    "width": [ref.width, v.width],
                    "height": [ref.height, v.height],
                },
            )


def merge_preflight_check(db: Session, video_ids: list[int]) -> list[Video]:
    if len(video_ids) < 2:
        raise api_error(400, "VALIDATION_ERROR", "至少选择 2 个视频")

    videos: list[Video] = []
    for vid in video_ids:
        v = db.get(Video, vid)
        if v is None or v.missing:
            raise api_error(404, "NOT_FOUND", f"视频 {vid} 不存在或已缺失")
        ensure_has_audio(v)
        if not Path(v.file_path).is_file():
            raise api_error(404, "NOT_FOUND", f"视频 {vid} 源文件不存在")
        videos.append(v)

    _validate_merge_videos(videos)
    return videos


def create_merge_videos_job(db: Session, body: MergeVideosRequest) -> Job:
    videos = merge_preflight_check(db, body.video_ids)
    first = videos[0]
    try:
        output_name = resolve_output_file_name(first.file_name, first.ext, body.output_file_name)
    except ValueError as exc:
        raise api_error(400, "VALIDATION_ERROR", str(exc)) from exc

    output_path = str(Path(first.file_path).parent / output_name)
    payload = {
        "video_ids": body.video_ids,
        "source_paths": [v.file_path for v in videos],
        "output_file_name": output_name,
        "output_path": output_path,
    }

    now = now_local_str()
    job = Job(
        type="merge_videos",
        status="queued",
        payload=json.dumps(payload, ensure_ascii=False),
        output_path=output_path,
        created_at=now,
    )
    db.add(job)
    db.flush()
    for idx, v in enumerate(videos):
        db.add(JobVideo(job_id=job.id, video_id=v.id, role=idx))
    db.commit()
    db.refresh(job)
    return job


def execute_video_clip_job(db: Session, job: Job) -> None:
    payload = json.loads(job.payload or "{}")
    source_path = payload["source_path"]
    output_path = Path(payload["output_path"])
    start_sec = float(payload["start_sec"])
    end_sec = payload.get("end_sec")
    end_sec = float(end_sec) if end_sec is not None else None
    video_id = int(payload["video_id"])

    if not Path(source_path).is_file():
        raise FfmpegError("源视频文件不存在")

    run_video_clip(source_path, output_path, start_sec, end_sec)

    job.result = json.dumps(
        {
            "output_path": str(output_path),
            "source_path": source_path,
            "source_video_id": video_id,
        },
        ensure_ascii=False,
    )
    job.output_path = str(output_path)


def execute_merge_videos_job(db: Session, job: Job) -> None:
    payload = json.loads(job.payload or "{}")
    source_paths = payload.get("source_paths") or []
    output_path = Path(payload["output_path"])
    video_ids = payload.get("video_ids") or []

    if len(source_paths) < 2:
        raise FfmpegError("合并任务参数无效：source_paths 不足 2 个")
    for p in source_paths:
        if not Path(p).is_file():
            raise FfmpegError(f"源视频文件不存在: {p}")

    run_merge_videos(source_paths, output_path)
    moved_sources = _move_merged_sources_to_delete(source_paths, output_path)

    job.result = json.dumps(
        {
            "output_path": str(output_path),
            "source_video_ids": video_ids,
            "moved_source_paths": moved_sources,
        },
        ensure_ascii=False,
    )
    job.output_path = str(output_path)


def _move_merged_sources_to_delete(source_paths: list[str], output_path: Path) -> list[str]:
    moved_paths: list[str] = []
    output_norm = str(output_path.resolve())

    for source in source_paths:
        source_path = Path(source)
        source_norm = str(source_path.resolve())
        if source_norm == output_norm:
            # Skip moving the merged output itself when output name matches one source.
            continue

        delete_dir = source_path.parent / "_delete"
        delete_dir.mkdir(parents=True, exist_ok=True)
        target_path = delete_dir / source_path.name
        try:
            if target_path.exists():
                target_path.unlink()
            shutil.move(str(source_path), str(target_path))
        except OSError as exc:
            raise FfmpegError(f"移动源视频到 _delete 失败: {source_path}") from exc
        moved_paths.append(str(target_path))

    return moved_paths


def get_source_videos(db: Session, job_id: int) -> list[dict]:
    rows = db.execute(
        select(JobVideo.video_id, JobVideo.role, Video.file_name)
        .join(Video, Video.id == JobVideo.video_id)
        .where(JobVideo.job_id == job_id)
        .order_by(JobVideo.role, JobVideo.video_id)
    ).all()
    return [{"id": vid, "file_name": name} for vid, _role, name in rows]


def job_to_dict(db: Session, job: Job, include_payload: bool = True) -> dict:
    result = json.loads(job.result) if job.result else None
    data: dict = {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "result": result,
        "error": job.error,
        "output_path": job.output_path,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "source_videos": get_source_videos(db, job.id),
    }
    if include_payload:
        data["payload"] = json.loads(job.payload) if job.payload else {}
    return data


def list_jobs(
    db: Session,
    page: int,
    page_size: int,
    job_type: str | None,
    status: str | None,
) -> dict:
    q = select(Job)
    count_q = select(func.count()).select_from(Job)
    if job_type:
        q = q.where(Job.type == job_type)
        count_q = count_q.where(Job.type == job_type)
    if status:
        q = q.where(Job.status == status)
        count_q = count_q.where(Job.status == status)

    total = db.scalar(count_q) or 0
    offset = (page - 1) * page_size
    jobs = db.scalars(q.order_by(Job.id.desc()).offset(offset).limit(page_size)).all()

    items = []
    for job in jobs:
        item = {
            "id": job.id,
            "type": job.type,
            "status": job.status,
            "output_path": job.output_path,
            "error": job.error,
            "created_at": job.created_at,
            "finished_at": job.finished_at,
            "source_videos": get_source_videos(db, job.id),
        }
        items.append(item)

    from app.schemas.common import paginate

    return paginate(items, page, page_size, total)


def retry_job(db: Session, job_id: int) -> Job:
    """Retry strategy: reset the same job to queued (fixed choice per API §7.6)."""
    job = db.get(Job, job_id)
    if job is None:
        raise api_error(404, "NOT_FOUND", "任务不存在")
    if job.status != "failed":
        raise api_error(400, "VALIDATION_ERROR", "仅失败任务可重试")

    job.status = "queued"
    job.error = None
    job.result = None
    job.started_at = None
    job.finished_at = None
    db.commit()
    db.refresh(job)
    return job
