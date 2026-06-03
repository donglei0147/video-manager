from pydantic import BaseModel, Field


class ThemeBackgroundBrief(BaseModel):
    id: int
    name: str
    image_url: str


class ThemeBackgroundOut(BaseModel):
    id: int
    name: str
    image_url: str
    source_video_id: int | None
    source_time_sec: float | None
    width: int | None
    height: int | None
    video_count: int = 0
    created_at: str
    updated_at: str


class ThemeBackgroundUpdate(BaseModel):
    name: str = Field(min_length=1)


class ThemeBackgroundFromFrame(BaseModel):
    time_sec: float = Field(ge=0)
    name: str | None = None
