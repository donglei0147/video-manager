from pathlib import Path

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.db.models import ThemeBackground
from app.db.session import get_db
from app.schemas.common import paginate
from app.schemas.theme_background import ThemeBackgroundUpdate
from app.services.theme_background_service import (
    delete_theme_background,
    list_theme_backgrounds,
    rename_theme_background,
    theme_background_out,
)

router = APIRouter(prefix="/theme-backgrounds", tags=["theme-backgrounds"])


@router.get("")
def get_theme_backgrounds(
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    keyword: str | None = Query(None),
    db: Session = Depends(get_db),
):
    items, total = list_theme_backgrounds(
        db, page=page, page_size=page_size, keyword=keyword
    )
    return paginate(items, page, page_size, total)


@router.get("/{background_id}")
def get_theme_background(background_id: int, db: Session = Depends(get_db)):
    bg = db.get(ThemeBackground, background_id)
    if bg is None:
        raise api_error(404, "NOT_FOUND", "主题背景图不存在")
    return theme_background_out(db, bg)


@router.get("/{background_id}/image")
def get_theme_background_image(background_id: int, db: Session = Depends(get_db)):
    bg = db.get(ThemeBackground, background_id)
    if bg is None:
        raise api_error(404, "NOT_FOUND", "主题背景图不存在")
    file_path = Path(bg.file_path)
    if not file_path.is_file():
        raise api_error(404, "FILE_NOT_FOUND", "主题背景图文件不存在")
    return FileResponse(
        path=str(file_path),
        media_type="image/jpeg",
        filename=f"{bg.name}.jpg",
    )


@router.patch("/{background_id}")
def patch_theme_background(
    background_id: int,
    body: ThemeBackgroundUpdate,
    db: Session = Depends(get_db),
):
    bg = db.get(ThemeBackground, background_id)
    if bg is None:
        raise api_error(404, "NOT_FOUND", "主题背景图不存在")
    bg = rename_theme_background(db, bg, body.name)
    return theme_background_out(db, bg)


@router.delete("/{background_id}", status_code=204)
def remove_theme_background(background_id: int, db: Session = Depends(get_db)):
    bg = db.get(ThemeBackground, background_id)
    if bg is None:
        raise api_error(404, "NOT_FOUND", "主题背景图不存在")
    delete_theme_background(db, bg)
    return Response(status_code=204)
