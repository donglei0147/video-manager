from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class PaginatedResponse(BaseModel):
    items: list
    page: int
    page_size: int
    total: int
    total_pages: int


def paginate(items: list, page: int, page_size: int, total: int) -> dict:
    total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 0
    if total == 0:
        total_pages = 0
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
