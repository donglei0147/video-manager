from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: int
    name: str


class TagListResponse(BaseModel):
    items: list[TagOut]


class TagCreate(BaseModel):
    name: str = Field(min_length=1)
