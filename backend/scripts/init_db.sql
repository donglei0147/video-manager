-- Video Manager schema (no foreign keys)
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS scan_folder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_scan_at TEXT,
    last_scan_status TEXT NOT NULL DEFAULT 'idle',
    last_scan_error TEXT,
    video_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_folder_id INTEGER NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_name TEXT NOT NULL,
    ext TEXT NOT NULL,
    file_size INTEGER NOT NULL DEFAULT 0,
    duration_sec REAL,
    width INTEGER,
    height INTEGER,
    video_codec TEXT,
    audio_codec TEXT,
    has_audio INTEGER NOT NULL DEFAULT 1,
    record_start_at TEXT,
    record_end_at TEXT,
    favorite_level INTEGER NOT NULL DEFAULT 0 CHECK (favorite_level >= 0 AND favorite_level <= 10),
    file_mtime TEXT,
    category_id INTEGER,
    metadata_status TEXT NOT NULL DEFAULT 'pending',
    missing INTEGER NOT NULL DEFAULT 0,
    indexed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS video_tag (
    video_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (video_id, tag_id)
);

CREATE TABLE IF NOT EXISTS job (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    payload TEXT,
    result TEXT,
    error TEXT,
    output_path TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime')),
    started_at TEXT,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS job_video (
    job_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    role INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, video_id)
);

CREATE INDEX IF NOT EXISTS ix_video_folder ON video(scan_folder_id);
CREATE INDEX IF NOT EXISTS ix_video_category ON video(category_id);
CREATE INDEX IF NOT EXISTS ix_video_favorite ON video(favorite_level);
CREATE INDEX IF NOT EXISTS ix_video_record_start ON video(record_start_at);
CREATE INDEX IF NOT EXISTS ix_video_record_end ON video(record_end_at);
CREATE INDEX IF NOT EXISTS ix_video_missing_status ON video(missing, metadata_status);
CREATE INDEX IF NOT EXISTS ix_video_mtime ON video(file_mtime);
CREATE INDEX IF NOT EXISTS ix_videotag_tag ON video_tag(tag_id);
CREATE INDEX IF NOT EXISTS ix_job_status ON job(status, type);
