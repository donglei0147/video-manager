from dataclasses import dataclass, field
from threading import Lock


@dataclass
class FolderScanProgress:
    phase: str = "idle"
    fast_processed: int = 0
    fast_total: int = 0
    metadata_processed: int = 0
    metadata_total: int = 0
    metadata_failed: int = 0
    last_error: str | None = None


_lock = Lock()
_progress: dict[int, FolderScanProgress] = {}
_global_progress = FolderScanProgress()


def get_progress(folder_id: int | None) -> FolderScanProgress:
    with _lock:
        if folder_id is None:
            return _global_progress
        return _progress.get(folder_id, FolderScanProgress())


def set_progress(folder_id: int | None, prog: FolderScanProgress) -> None:
    with _lock:
        if folder_id is None:
            global _global_progress
            _global_progress = prog
        else:
            _progress[folder_id] = prog


def clear_progress(folder_id: int) -> None:
    with _lock:
        _progress.pop(folder_id, None)
