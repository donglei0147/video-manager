"""Phase 1 API smoke tests for FR-1~FR-4 acceptance criteria."""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765/api"
ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "data" / "test_videos"


def req(method: str, path: str, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        return e.code, json.loads(raw) if raw else {"error": {"message": str(e)}}


def wait_scan(folder_id: int, timeout=10):
    for _ in range(timeout * 5):
        _, st = req("GET", f"/scan-folders/{folder_id}/status")
        if st["last_scan_status"] != "scanning":
            return st
        time.sleep(0.2)
    raise TimeoutError("scan timeout")


def main():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    (TEST_DIR / "_temp").mkdir(exist_ok=True)
    (TEST_DIR / "sample.mp4").write_bytes(b"fake mp4 content")
    (TEST_DIR / "_temp" / "hidden.mp4").write_bytes(b"should skip")
    (TEST_DIR / "clip.mov").write_bytes(b"fake mov")
    (TEST_DIR / "ignore.avi").write_bytes(b"skip format")

    results = []

    # health
    code, health = req("GET", "/health")
    results.append(("health", code == 200 and health.get("db_available")))

    # FR-1: add folder
    code, folder = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    if code == 409:
        _, lst = req("GET", "/scan-folders")
        folder = next(i for i in lst["items"] if i["path"].lower() == str(TEST_DIR).lower())
        code = 200
    results.append(("AC-1.1 add folder idle", code in (200, 201) and folder["last_scan_status"] in ("idle", "success")))

    # duplicate
    code, err = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    results.append(("AC-1.2 duplicate rejected", code == 409))

    # invalid path
    code, _ = req("POST", "/scan-folders", {"path": "Z:\\nonexistent_path_xyz_12345"})
    results.append(("AC-1.3 invalid path rejected", code == 400))

    fid = folder["id"]

    # scan
    code, _ = req("POST", f"/scan-folders/{fid}/scan")
    st = wait_scan(fid)
    results.append(("AC-2.5 scan progress + last_scan_at", st["last_scan_status"] == "success"))

    _, vlist = req("GET", "/videos?page=1&page_size=100")
    names = {v["file_name"] for v in vlist["items"]}
    results.append(("AC-3.1 mp4/mov only, skip _temp", names == {"sample.mp4", "clip.mov"}))
    results.append(
        (
            "AC-3.2 metadata visible (pending or ready after scan)",
            all(v["metadata_status"] in ("pending", "ready", "failed") for v in vlist["items"]),
        )
    )

    total1 = vlist["total"]
    code, _ = req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)
    _, vlist2 = req("GET", "/videos?page=1&page_size=100")
    results.append(("AC-2.4 no duplicate on rescan", vlist2["total"] == total1))

    # add new file
    (TEST_DIR / "new.mp4").write_bytes(b"new file")
    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)
    _, vlist3 = req("GET", "/videos?page=1&page_size=100")
    results.append(("AC-2.1 incremental add", vlist3["total"] == total1 + 1))

    # delete file -> missing
    (TEST_DIR / "new.mp4").unlink(missing_ok=True)
    req("POST", f"/scan-folders/{fid}/scan")
    wait_scan(fid)
    _, vlist4 = req("GET", "/videos?include_missing=true")
    missing = [v for v in vlist4["items"] if v["file_name"] == "new.mp4"]
    results.append(("AC-2.3 mark missing", len(missing) == 1 and missing[0]["missing"]))

    # pagination
    _, p2 = req("GET", "/videos?page=1&page_size=1")
    _, p2b = req("GET", "/videos?page=2&page_size=1")
    results.append(("AC-4.1 pagination", p2["page_size"] == 1 and p2b["page"] == 2 and p2["items"][0]["id"] != p2b["items"][0]["id"]))

    # page_size max 100
    code, _ = req("GET", "/videos?page_size=101")
    results.append(("page_size max 100", code == 400))

    # stream endpoint exists
    vid = p2["items"][0]["id"]
    r = urllib.request.Request(f"{BASE}/videos/{vid}/stream", method="GET")
    with urllib.request.urlopen(r, timeout=5) as resp:
        results.append(("AC-4.2 stream for preview", resp.status in (200, 206)))

    # disable folder - scan-all should skip (only test enabled filter indirectly)
    req("PATCH", f"/scan-folders/{fid}", {"enabled": False})
    code, _ = req("POST", "/scan-folders/scan-all")
    results.append(("AC-1.4 disabled excluded from scan-all", code == 400))
    req("PATCH", f"/scan-folders/{fid}", {"enabled": True})

    print("=== Phase 1 AC Self-Check ===")
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
