from fastapi import HTTPException


def api_error(status: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return HTTPException(status_code=status, detail=body)
