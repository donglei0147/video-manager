"""Phase 4 smoke tests: merge preflight + merge videos."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("VIDEO_API_BASE", "http://127.0.0.1:8765/api")
ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "data" / "test_videos_phase4"
DB_PATH = ROOT / "data" / "app.db"
SRC1 = TEST_DIR / "m1.mp4"
SRC2 = TEST_DIR / "m2.mp4"
SRC_BAD = TEST_DIR / "m_bad.mov"


def req(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw) if raw else {"error": {"message": str(e)}}
        except json.JSONDecodeError:
            payload = {"error": {"code": "HTTP_ERROR", "message": str(e)}}
        return e.code, payload


def wait_scan(folder_id: int, timeout=120):
    for _ in range(timeout * 5):
        _, st = req("GET", f"/scan-folders/{folder_id}/status")
        if st["last_scan_status"] != "scanning":
            return st
        time.sleep(0.2)
    raise TimeoutError("scan timeout")


def wait_job(job_id: int, timeout=120):
    for _ in range(timeout * 10):
        _, job = req("GET", f"/jobs/{job_id}")
        if job["status"] in ("success", "failed"):
            return job
        time.sleep(0.1)
    raise TimeoutError(f"job {job_id} timeout")


def ffmpeg_make(path: Path, duration: int, size: str = "320x240") -> bool:
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={size}:rate=30",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=120)
    return proc.returncode == 0 and path.is_file()


def ensure_test_videos() -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    ok = ffmpeg_make(SRC1, 6) and ffmpeg_make(SRC2, 7) and ffmpeg_make(SRC_BAD, 6, "640x360")
    return ok


def set_video_metadata(video_id: int, width: int, height: int, ext: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        UPDATE video SET
            duration_sec=10.0,
            has_audio=1,
            metadata_status='ready',
            video_codec='h264',
            audio_codec='aac',
            width=?,
            height=?,
            ext=?
        WHERE id=?
        """,
        (width, height, ext, video_id),
    )
    conn.commit()
    conn.close()


def main():
    if not ensure_test_videos():
        print("SKIP: ffmpeg not available for phase4 test videos")
        return 0

    results = []

    code, folder = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    if code == 409:
        _, lst = req("GET", "/scan-folders")
        folder = next(i for i in lst["items"] if i["path"].lower() == str(TEST_DIR).lower())
    fid = folder["id"]
    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)

    _, vlist = req("GET", "/videos?page=1&page_size=100&q=m")
    idx = {v["file_name"]: v["id"] for v in vlist["items"]}
    id1, id2, id_bad = idx["m1.mp4"], idx["m2.mp4"], idx["m_bad.mov"]

    set_video_metadata(id1, 320, 240, "mp4")
    set_video_metadata(id2, 320, 240, "mp4")
    set_video_metadata(id_bad, 640, 360, "mov")

    # preflight ok
    code_ok, data_ok = req("POST", "/jobs/merge-videos/preflight", {"video_ids": [id1, id2]})
    results.append(("preflight success", code_ok == 200 and data_ok.get("ok") is True))

    # preflight mismatch
    code_m, data_m = req("POST", "/jobs/merge-videos/preflight", {"video_ids": [id1, id_bad]})
    results.append(
        (
            "CODEC_MISMATCH returned",
            code_m == 409 and data_m.get("error", {}).get("code") == "CODEC_MISMATCH",
        )
    )

    # merge job
    src1_before = SRC1.stat().st_size
    src2_before = SRC2.stat().st_size
    code_j, created = req(
        "POST",
        "/jobs/merge-videos",
        {"video_ids": [id1, id2], "output_file_name": "merged_out.mp4"},
    )
    results.append(("merge enqueue 202", code_j == 202 and created.get("type") == "merge_videos"))
    if code_j == 202 and created.get("job_id"):
        job = wait_job(created["job_id"])
        out_path = Path(job["result"]["output_path"]) if job.get("result") else Path("")
        results.append(("merge execution success", job["status"] == "success" and out_path.is_file()))
    else:
        results.append(("merge execution success", False))
    results.append(
        (
            "source files preserved",
            SRC1.is_file() and SRC2.is_file() and SRC1.stat().st_size == src1_before and SRC2.stat().st_size == src2_before,
        )
    )

    print("=== Phase 4 AC Self-Check ===")
    passed = 0
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {name}")
        if ok:
            passed += 1
    print(f"\n{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
