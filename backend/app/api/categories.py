from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import Category, Video
from app.db.session import get_db
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryOut,
    CategoryUpdate,
)
from app.utils import now_local_str

router = APIRouter(prefix="/categories", tags=["categories"])


def _category_out(db: Session, cat: Category) -> CategoryOut:
    count = db.scalar(
        select(func.count()).select_from(Video).where(Video.category_id == cat.id)
    )
    return CategoryOut(
        id=cat.id,
        name=cat.name,
        sort_order=cat.sort_order,
        video_count=count or 0,
    )


@router.get("", response_model=CategoryListResponse)
def list_categories(db: Session = Depends(get_db)):
    cats = db.scalars(select(Category).order_by(Category.sort_order, Category.id)).all()
    return CategoryListResponse(items=[_category_out(db, c) for c in cats])


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, db: Session = Depends(get_db)):
    name = body.name.strip()
    if not name:
        raise api_error(400, "VALIDATION_ERROR", "分类名称不能为空")
    existing = db.scalar(select(Category).where(Category.name == name))
    if existing:
        raise api_error(409, "CONFLICT", "分类名称已存在")
    cat = Category(name=name, sort_order=body.sort_order, created_at=now_local_str())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return _category_out(db, cat)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, body: CategoryUpdate, db: Session = Depends(get_db)
):
    cat = db.get(Category, category_id)
    if cat is None:
        raise api_error(404, "NOT_FOUND", "分类不存在")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        name = data["name"].strip()
        if not name:
            raise api_error(400, "VALIDATION_ERROR", "分类名称不能为空")
        dup = db.scalar(
            select(Category).where(Category.name == name, Category.id != category_id)
        )
        if dup:
            raise api_error(409, "CONFLICT", "分类名称已存在")
        cat.name = name
    if "sort_order" in data:
        cat.sort_order = data["sort_order"]
    db.commit()
    db.refresh(cat)
    return _category_out(db, cat)


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.get(Category, category_id)
    if cat is None:
        raise api_error(404, "NOT_FOUND", "分类不存在")
    videos = db.scalars(select(Video).where(Video.category_id == category_id)).all()
    for v in videos:
        v.category_id = None
    db.delete(cat)
    db.commit()
    return Response(status_code=204)
