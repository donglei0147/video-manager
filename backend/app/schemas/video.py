from pydantic import BaseModel, Field


class CategoryBrief(BaseModel):
    id: int
    name: str


class TagBrief(BaseModel):
    id: int
    name: str


class ThemeBackgroundBrief(BaseModel):
    id: int
    name: str
    image_url: str


class VideoSummary(BaseModel):
    id: int
    file_name: str
    ext: str
    file_size: int
    duration_sec: float | None
    width: int | None
    height: int | None
    record_start_at: str | None
    record_end_at: str | None
    favorite_level: int
    file_mtime: str | None
    metadata_status: str
    missing: bool
    playback_supported: bool
    has_audio: bool
    category: CategoryBrief | None
    tags: list[TagBrief]
    theme_background: ThemeBackgroundBrief | None
    stream_url: str


class VideoDetail(VideoSummary):
    scan_folder_id: int
    file_path: str
    video_codec: str | None
    audio_codec: str | None
    indexed_at: str
    updated_at: str


class VideoUpdate(BaseModel):
    category_id: int | None = None
    tag_ids: list[int] | None = None
    record_start_at: str | None = None
    record_end_at: str | None = None
    favorite_level: int | None = None
