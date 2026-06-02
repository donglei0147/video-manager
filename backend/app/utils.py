import re
from datetime import datetime
from pathlib import Path

DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


def now_local_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_mtime(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def normalize_path(path: str) -> str:
    return str(Path(path).resolve())


def is_video_ext(path: Path) -> bool:
    return path.suffix.lower() in {".mp4", ".mov"}


def is_valid_datetime(s: str) -> bool:
    if not DATETIME_PATTERN.match(s):
        return False
    try:
        datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def playback_supported(video_codec: str | None, audio_codec: str | None, metadata_status: str, missing: bool) -> bool:
    if missing or metadata_status != "ready":
        return False
    if not video_codec:
        return False
    vc = video_codec.lower()
    ac = (audio_codec or "").lower()
    if vc == "h264" and (ac in ("aac", "") or audio_codec is None):
        return True
    return False
