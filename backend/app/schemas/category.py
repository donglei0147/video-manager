from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    id: int
    name: str
    sort_order: int
    video_count: int = 0


class CategoryListResponse(BaseModel):
    items: list[CategoryOut]


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
