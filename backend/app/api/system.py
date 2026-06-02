from fastapi import APIRouter, Response

from app.api.errors import api_error
from app.services.folder_picker import pick_folder_dialog
from app.utils import normalize_path

router = APIRouter(prefix="/system", tags=["system"])


@router.post("/pick-folder")
def pick_folder():
    path = pick_folder_dialog()
    if not path:
        return Response(status_code=204)
    return {"path": normalize_path(path)}
