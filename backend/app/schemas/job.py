from pydantic import BaseModel, Field


class VideoClipRequest(BaseModel):
    video_id: int
    start_sec: float = Field(ge=0)
    end_sec: float | None = None
    output_file_name: str | None = None


class VideoClipResponse(BaseModel):
    job_id: int
    type: str
    status: str


class JobSourceVideo(BaseModel):
    id: int
    file_name: str


class JobDetail(BaseModel):
    id: int
    type: str
    status: str
    payload: dict
    result: dict | None
    error: str | None
    output_path: str | None
    created_at: str
    started_at: str | None
    finished_at: str | None
    source_videos: list[JobSourceVideo]


class JobSummary(BaseModel):
    id: int
    type: str
    status: str
    output_path: str | None
    error: str | None
    created_at: str
    finished_at: str | None
    source_videos: list[JobSourceVideo]


class JobListResponse(BaseModel):
    items: list[JobSummary]
    page: int
    page_size: int
    total: int
    total_pages: int


class MergePreflightRequest(BaseModel):
    video_ids: list[int] = Field(min_length=1)


class MergePreflightResponse(BaseModel):
    ok: bool
    video_ids: list[int]


class MergeVideosRequest(BaseModel):
    video_ids: list[int] = Field(min_length=2)
    output_file_name: str | None = None
