"""Phase 3 smoke tests: video-clip to {source}/_temp/, overwrite, source preserved."""
import json
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765/api"
ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "data" / "test_videos_phase3"
DB_PATH = ROOT / "data" / "app.db"
SOURCE = TEST_DIR / "clip_source.mp4"


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


def ensure_test_video() -> bool:
    if shutil.which("ffmpeg") is None:
        return False
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    if SOURCE.is_file():
        return True
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=duration=12:size=320x240:rate=30",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:duration=12",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-shortest",
        str(SOURCE),
    ]
    proc = subprocess.run(cmd, capture_output=True, timeout=60)
    return proc.returncode == 0 and SOURCE.is_file()


def set_video_metadata(video_id: int, duration_sec: float):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        UPDATE video SET duration_sec=?, has_audio=1, metadata_status='ready',
        video_codec='h264', audio_codec='aac', width=320, height=240
        WHERE id=?
        """,
        (duration_sec, video_id),
    )
    conn.commit()
    conn.close()


def main():
    if not ensure_test_video():
        print("SKIP: ffmpeg not available to generate test video")
        return 0

    results = []

    code, folder = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    if code == 409:
        _, lst = req("GET", "/scan-folders")
        folder = next(i for i in lst["items"] if i["path"].lower() == str(TEST_DIR).lower())
    fid = folder["id"]

    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)

    _, vlist = req("GET", f"/videos?page=1&page_size=100&q=clip_source")
    vid = next(v["id"] for v in vlist["items"] if v["file_name"] == "clip_source.mp4")
    set_video_metadata(vid, 12.0)

    source_mtime_before = SOURCE.stat().st_mtime
    source_size_before = SOURCE.stat().st_size

    # AC-8.1 clip from start to end (no end_sec)
    code, created = req("POST", "/jobs/video-clip", {"video_id": vid, "start_sec": 3.0})
    results.append(("AC-8/API 202 queued", code == 202 and created.get("status") == "queued"))
    job1 = wait_job(created["job_id"])
    out1 = Path(job1["result"]["output_path"])
    results.append(("AC-8.1 clip to end success", job1["status"] == "success"))
    results.append(("AC-8.3 output under _temp", "_temp" in str(out1) and out1.suffix == ".mp4"))
    results.append(("AC-8.4 source file preserved", SOURCE.is_file()))
    results.append(
        (
            "AC-8.4 source unchanged on disk",
            SOURCE.stat().st_mtime == source_mtime_before and SOURCE.stat().st_size == source_size_before,
        )
    )

    # AC-8.2 clip with end_sec
    code2, created2 = req(
        "POST",
        "/jobs/video-clip",
        {"video_id": vid, "start_sec": 2.0, "end_sec": 8.0},
    )
    results.append(("clip with end_sec accepted", code2 == 202))
    job2 = wait_job(created2["job_id"])
    results.append(("AC-8.2 bounded clip success", job2["status"] == "success"))

    # AC-8.8 overwrite same name
    code3, created3 = req(
        "POST",
        "/jobs/video-clip",
        {"video_id": vid, "start_sec": 1.0, "end_sec": 5.0, "output_file_name": "clip_source.mp4"},
    )
    job3 = wait_job(created3["job_id"])
    results.append(("AC-8.8 overwrite same name success", job3["status"] == "success"))
    results.append(("AC-8.8 output path unchanged", Path(job3["result"]["output_path"]) == out1))

    # validation: end_sec <= start_sec
    code_bad, err = req(
        "POST",
        "/jobs/video-clip",
        {"video_id": vid, "start_sec": 5.0, "end_sec": 5.0},
    )
    results.append(
        (
            "end_sec validation",
            code_bad == 400 and err.get("error", {}).get("code") == "VALIDATION_ERROR",
        )
    )

    print("=== Phase 3 AC Self-Check ===")
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
