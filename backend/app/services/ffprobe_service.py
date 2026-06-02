import json
import subprocess
from dataclasses import dataclass

from app.config import settings


@dataclass
class ProbeResult:
    duration_sec: float | None
    width: int | None
    height: int | None
    video_codec: str | None
    audio_codec: str | None
    has_audio: bool


def probe_video(file_path: str) -> ProbeResult | None:
    """Run ffprobe; return None on command failure."""
    cmd = [
        settings.ffprobe_path,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0 or not stdout:
        return None

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return None

    streams = data.get("streams") or []
    fmt = data.get("format") or {}

    video_codec: str | None = None
    audio_codec: str | None = None
    width: int | None = None
    height: int | None = None
    has_audio = False

    for stream in streams:
        codec_type = stream.get("codec_type")
        codec_name = stream.get("codec_name")
        if codec_type == "video" and video_codec is None:
            video_codec = codec_name
            width = stream.get("width")
            height = stream.get("height")
        elif codec_type == "audio":
            has_audio = True
            if audio_codec is None:
                audio_codec = codec_name

    duration_sec: float | None = None
    dur = fmt.get("duration")
    if dur is not None:
        try:
            duration_sec = float(dur)
        except (TypeError, ValueError):
            pass

    return ProbeResult(
        duration_sec=duration_sec,
        width=int(width) if width is not None else None,
        height=int(height) if height is not None else None,
        video_codec=video_codec,
        audio_codec=audio_codec,
        has_audio=has_audio,
    )
