import subprocess
import tempfile
from pathlib import Path

from app.config import settings


class FfmpegError(Exception):
    def __init__(self, message: str, returncode: int | None = None):
        super().__init__(message)
        self.returncode = returncode


def clip_output_path(source_path: str, output_file_name: str) -> Path:
    """Return {source_dir}/_temp/{output_file_name}."""
    source = Path(source_path)
    return source.parent / "_temp" / output_file_name


def resolve_output_file_name(video_file_name: str, video_ext: str, custom_name: str | None) -> str:
    name = (custom_name or video_file_name).strip()
    if not name:
        raise ValueError("输出文件名不能为空")
    if "/" in name or "\\" in name or name in (".", ".."):
        raise ValueError("输出文件名非法")
    ext = Path(name).suffix.lower()
    expected = video_ext if video_ext.startswith(".") else f".{video_ext}"
    if ext != expected.lower():
        raise ValueError(f"输出扩展名须与源视频一致（{expected}）")
    return name


def run_video_clip(
    input_path: str,
    output_path: Path,
    start_sec: float,
    end_sec: float | None,
) -> None:
    """Execute ffmpeg clip per ffmpeg-strategy §3.2 (-ss after -i, -c copy, -y overwrite)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        settings.ffmpeg_path,
        "-y",
        "-i",
        input_path,
        "-ss",
        str(start_sec),
    ]
    if end_sec is not None:
        cmd.extend(["-to", str(end_sec)])
    cmd.extend(["-c", "copy", str(output_path)])

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FfmpegError(str(exc)) from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        tail = stderr[-2000:] if len(stderr) > 2000 else stderr
        raise FfmpegError(tail or f"ffmpeg exited with code {proc.returncode}", proc.returncode)


def _escape_concat_path(path: str) -> str:
    return path.replace("'", "'\\''")


def run_merge_videos(input_paths: list[str], output_path: Path) -> None:
    """Execute concat demuxer merge per ffmpeg-strategy §4.2."""
    if len(input_paths) < 2:
        raise FfmpegError("合并至少需要 2 个视频")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    )
    try:
        with tmp_file as f:
            for p in input_paths:
                f.write(f"file '{_escape_concat_path(p)}'\n")

        cmd = [
            settings.ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            tmp_file.name,
            "-c",
            "copy",
            str(output_path),
        ]
        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3600,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise FfmpegError(str(exc)) from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
            tail = stderr[-2000:] if len(stderr) > 2000 else stderr
            raise FfmpegError(tail or f"ffmpeg exited with code {proc.returncode}", proc.returncode)
    finally:
        Path(tmp_file.name).unlink(missing_ok=True)
