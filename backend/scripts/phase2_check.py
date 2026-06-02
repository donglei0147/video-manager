"""Phase 2 API smoke tests for FR-3 (metadata), FR-5~7, FR-13."""
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8765/api"
ROOT = Path(__file__).resolve().parents[2]
TEST_DIR = ROOT / "data" / "test_videos_phase2"
DB_PATH = ROOT / "data" / "app.db"


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


def get_or_create(method: str, path: str, body: dict, list_path: str, match_key: str):
    code, data = req(method, path, body)
    if code in (200, 201):
        return data
    if code == 409:
        _, lst = req("GET", list_path)
        name = body.get("name")
        for item in lst["items"]:
            if item.get(match_key) == name or item.get("name") == name:
                return item
    raise RuntimeError(f"get_or_create failed for {path}: {code} {data}")


def wait_scan(folder_id: int, timeout=120):
    for _ in range(timeout * 5):
        _, st = req("GET", f"/scan-folders/{folder_id}/status")
        if st["last_scan_status"] != "scanning":
            return st
        time.sleep(0.2)
    raise TimeoutError("scan timeout")


def set_video_has_audio(video_id: int, has_audio: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE video SET has_audio=? WHERE id=?", (has_audio, video_id))
    conn.commit()
    conn.close()


def main():
    TEST_DIR.mkdir(parents=True, exist_ok=True)
    (TEST_DIR / "sample.mp4").write_bytes(b"fake mp4")
    results = []

    code, folder = req("POST", "/scan-folders", {"path": str(TEST_DIR)})
    if code == 409:
        _, lst = req("GET", "/scan-folders")
        folder = next(i for i in lst["items"] if i["path"].lower() == str(TEST_DIR).lower())
    fid = folder["id"]

    req("POST", f"/scan-folders/{fid}/scan")
    st = wait_scan(fid)
    results.append(
        (
            "metadata phase completed",
            st.get("phase") == "idle" and st["last_scan_status"] in ("success", "failed"),
        )
    )

    _, vlist = req("GET", f"/videos?page=1&page_size=100&q=test_videos_phase2")
    phase2_items = vlist["items"]
    results.append(
        (
            "AC-3.3/3.4 metadata status ready or failed",
            len(phase2_items) >= 1
            and all(v["metadata_status"] in ("ready", "failed") for v in phase2_items),
        )
    )

    # FR-7: category + tags + record time + favorite
    cat = get_or_create(
        "POST",
        "/categories",
        {"name": "Phase2测试分类", "sort_order": 0},
        "/categories",
        "name",
    )
    tag1 = get_or_create(
        "POST", "/tags", {"name": "phase2_tag_a"}, "/tags?q=phase2_tag_a", "name"
    )
    tag2 = get_or_create(
        "POST", "/tags", {"name": "phase2_tag_b"}, "/tags?q=phase2_tag_b", "name"
    )
    vid = phase2_items[0]["id"]

    code, updated = req(
        "PATCH",
        f"/videos/{vid}",
        {
            "category_id": cat["id"],
            "tag_ids": [tag1["id"], tag2["id"]],
            "record_start_at": "2024-03-15 14:30:00",
            "record_end_at": None,
            "favorite_level": 8,
        },
    )
    results.append(("AC-7.1 category saved", updated.get("category", {}).get("id") == cat["id"]))
    results.append(("AC-7.2 tags saved", len(updated.get("tags", [])) == 2))
    results.append(("AC-7.3 record start only", updated.get("record_start_at") == "2024-03-15 14:30:00"))
    results.append(("AC-7.5 favorite in detail", updated.get("favorite_level") == 8))

    req("PATCH", f"/videos/{vid}", {"record_start_at": None, "record_end_at": None})
    _, filtered = req("GET", "/videos?record_start_from=2024-01-01&record_start_to=2025-01-01")
    results.append(
        (
            "AC-7.4 cleared record time excluded from range filter",
            all(item["id"] != vid for item in filtered["items"]),
        )
    )

    req(
        "PATCH",
        f"/videos/{vid}",
        {
            "record_start_at": "2024-06-01 10:00:00",
            "favorite_level": 8,
            "category_id": cat["id"],
            "tag_ids": [tag1["id"], tag2["id"]],
        },
    )

    # FR-5 filters
    _, byCat = req("GET", f"/videos?category_id={cat['id']}")
    results.append(("AC-5.1 category filter", all(v["category"]["id"] == cat["id"] for v in byCat["items"])))

    _, byTags = req("GET", f"/videos?tag_ids={tag1['id']},{tag2['id']}")
    results.append(
        (
            "AC-5.2 tag AND filter",
            vid in [v["id"] for v in byTags["items"]],
        )
    )

    _, byQ = req("GET", "/videos?q=sample")
    results.append(("AC-5.3 keyword filter", any(v["file_name"] == "sample.mp4" for v in byQ["items"])))

    _, byRec = req(
        "GET",
        "/videos?record_start_from=2024-06-01%2000:00:00&record_start_to=2024-06-02%2000:00:00",
    )
    results.append(
        (
            "AC-5.4 record start range",
            any(v["id"] == vid for v in byRec["items"]),
        )
    )

    _, byFav = req("GET", "/videos?favorite_min=8")
    results.append(
        (
            "AC-5.5 favorite_min",
            all(v["favorite_level"] >= 8 for v in byFav["items"]),
        )
    )

    _, combo = req(
        "GET",
        f"/videos?category_id={cat['id']}&favorite_min=8&q=sample",
    )
    results.append(
        (
            "AC-5.6 combined filters",
            len(combo["items"]) >= 1 and combo["items"][0]["id"] == vid,
        )
    )

    _, sortDesc = req("GET", "/videos?sort=favorite_desc&page_size=100")
    levels = [v["favorite_level"] for v in sortDesc["items"]]
    results.append(
        (
            "AC-5.7 favorite sort",
            levels == sorted(levels, reverse=True),
        )
    )

    # FR-6 Range
    stream_url = f"{BASE}/videos/{vid}/stream"
    r = urllib.request.Request(stream_url, method="GET")
    with urllib.request.urlopen(r, timeout=10) as resp:
        results.append(("AC-6.1 stream 200", resp.status == 200))
        accept_ranges = resp.headers.get("Accept-Ranges", "")

    r2 = urllib.request.Request(
        stream_url,
        method="GET",
        headers={"Range": "bytes=0-99"},
    )
    with urllib.request.urlopen(r2, timeout=10) as resp:
        results.append(
            (
                "AC-6.2 Range 206",
                resp.status == 206 and resp.headers.get("Content-Range", "").startswith("bytes "),
            )
        )
    results.append(("AC-6 Range Accept-Ranges", accept_ranges == "bytes"))

    _, detail = req("GET", f"/videos/{vid}")
    results.append(
        (
            "AC-6.5 playback_supported field",
            "playback_supported" in detail,
        )
    )

    # FR-13 no audio
    set_video_has_audio(vid, 0)
    code, err = req(
        "POST",
        "/jobs/video-clip",
        {"video_id": vid, "start_sec": 0},
    )
    results.append(
        (
            "AC-13.1 clip blocked without audio",
            code == 400 and err.get("error", {}).get("code") == "NO_AUDIO_TRACK",
        )
    )
    results.append(
        (
            "AC-13.2 clear no-audio message",
            "无音频" in err.get("error", {}).get("message", ""),
        )
    )

    code, err2 = req("POST", "/jobs/merge-videos/preflight", {"video_ids": [vid, vid]})
    results.append(
        (
            "AC-13.1 merge preflight blocked",
            code == 400 and err2.get("error", {}).get("code") == "NO_AUDIO_TRACK",
        )
    )

    set_video_has_audio(vid, 1)

    print("=== Phase 2 AC Self-Check ===")
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
