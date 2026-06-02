from pydantic import BaseModel, Field


class ScanFolderCreate(BaseModel):
    path: str


class ScanFolderUpdate(BaseModel):
    enabled: bool | None = None


class ScanFolderOut(BaseModel):
    id: int
    path: str
    enabled: bool
    last_scan_at: str | None
    last_scan_status: str
    last_scan_error: str | None = None
    video_count: int
    created_at: str

    class Config:
        from_attributes = True


class ScanFolderListResponse(BaseModel):
    items: list[ScanFolderOut]


class ScanStartResponse(BaseModel):
    scan_folder_id: int | None
    status: str
    phase: str
    processed: int
    total: int


class ScanStatusResponse(BaseModel):
    scan_folder_id: int | None
    last_scan_status: str
    phase: str
    last_scan_error: str | None = None
    fast_scan: dict
    metadata_scan: dict
