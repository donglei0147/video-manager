"""Phase 5 checks: incremental scan, open-folder, jobs list & retry."""
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = os.environ.get("VIDEO_API_BASE", "http://127.0.0.1:8765/api")
ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "data" / "test_videos_phase5"
DB_PATH = ROOT / "data" / "app.db"
INC_FILE = TEST_DIR / "inc.mp4"
BAD_FILE = TEST_DIR / "broken.mp4"


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


def patch_video_ready(video_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        UPDATE video
        SET metadata_status='ready', has_audio=1, duration_sec=10.0,
            video_codec='h264', audio_codec='aac', width=320, height=240
        WHERE id=?
        """,
        (video_id,),
    )
    conn.commit()
    conn.close()


def main():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    INC_FILE.write_bytes(b"phase5-incremental-v1")
    BAD_FILE.write_bytes(b"not-a-real-video")

    results = []

    # Ensure folder exists
    code, folder = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    if code == 409:
        _, lst = req("GET", "/scan-folders")
        folder = next(i for i in lst["items"] if i["path"].lower() == str(TEST_DIR).lower())
    fid = folder["id"]

    # Scan once
    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)
    _, vlist = req("GET", "/videos?page=1&page_size=100&q=inc.mp4")
    vid = vlist["items"][0]["id"]

    # Set annotations then mutate file and rescan
    req(
        "PATCH",
        f"/videos/{vid}",
        {
            "record_start_at": "2024-01-01 00:00:00",
            "favorite_level": 7,
            "record_end_at": None,
        },
    )
    time.sleep(1.1)
    INC_FILE.write_bytes(b"phase5-incremental-v2-more-bytes")

    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)
    _, detail = req("GET", f"/videos/{vid}")
    results.append(("incremental keeps annotations", detail["favorite_level"] == 7))
    results.append(("incremental keeps record_start_at", detail["record_start_at"] == "2024-01-01 00:00:00"))

    # open-folder API
    code_open, _ = req("POST", f"/videos/{vid}/open-folder")
    results.append(("open-folder endpoint", code_open == 204))

    # Create a failed job by clipping bad file then retry
    _, bad_list = req("GET", "/videos?page=1&page_size=100&q=broken.mp4")
    bad_vid = bad_list["items"][0]["id"]
    patch_video_ready(bad_vid)
    code_job, created = req("POST", "/jobs/video-clip", {"video_id": bad_vid, "start_sec": 0})
    results.append(("create failed-target job", code_job == 202))
    done = wait_job(created["job_id"])
    results.append(("job reaches failed", done["status"] == "failed"))

    # list jobs + retry
    code_list, jobs = req("GET", "/jobs?page=1&page_size=20&type=video_clip&status=failed")
    results.append(("list failed jobs", code_list == 200 and isinstance(jobs.get("items"), list)))
    code_retry, retried = req("POST", f"/jobs/{done['id']}/retry")
    results.append(("retry endpoint accepted", code_retry == 202 and retried.get("status") == "queued"))

    print("=== Phase 5 AC Self-Check ===")
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
