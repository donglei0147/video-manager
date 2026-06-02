from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import Tag, VideoTag
from app.db.session import get_db
from app.schemas.tag import TagCreate, TagListResponse, TagOut
from app.utils import now_local_str

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=TagListResponse)
def list_tags(
    q: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Tag).order_by(Tag.name)
    if q:
        stmt = stmt.where(Tag.name.like(f"{q}%"))
    tags = db.scalars(stmt.limit(limit)).all()
    return TagListResponse(items=[TagOut(id=t.id, name=t.name) for t in tags])


@router.post("", response_model=TagOut, status_code=201)
def create_tag(body: TagCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise api_error(400, "VALIDATION_ERROR", "标签名称不能为空")
    existing = db.scalar(select(Tag).where(Tag.name == name))
    if existing:
        raise api_error(409, "CONFLICT", "标签名称已存在")
    tag = Tag(name=name, created_at=now_local_str())
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return TagOut(id=tag.id, name=tag.name)


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.get(Tag, tag_id)
    if tag is None:
        raise api_error(404, "NOT_FOUND", "标签不存在")
    db.execute(delete(VideoTag).where(VideoTag.tag_id == tag_id))
    db.delete(tag)
    db.commit()
    return Response(status_code=204)
