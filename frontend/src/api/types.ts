export interface ScanFolder {
  id: number;
  path: string;
  enabled: boolean;
  last_scan_at: string | null;
  last_scan_status: string;
  last_scan_error: string | null;
  video_count: number;
  created_at: string;
}

export interface CategoryBrief {
  id: number;
  name: string;
}

export interface TagBrief {
  id: number;
  name: string;
}

export interface VideoSummary {
  id: number;
  file_name: string;
  ext: string;
  file_size: number;
  duration_sec: number | null;
  width: number | null;
  height: number | null;
  record_start_at: string | null;
  record_end_at: string | null;
  favorite_level: number;
  file_mtime: string | null;
  metadata_status: string;
  missing: boolean;
  playback_supported: boolean;
  has_audio: boolean;
  category: CategoryBrief | null;
  tags: TagBrief[];
  stream_url: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ScanStatus {
  scan_folder_id: number;
  last_scan_status: string;
  phase: string;
  last_scan_error: string | null;
  fast_scan: { processed: number; total: number };
  metadata_scan: { processed: number; total: number; failed: number };
}

export interface JobSourceVideo {
  id: number;
  file_name: string;
}

export interface JobSummary {
  id: number;
  type: string;
  status: string;
  output_path: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
  source_videos: JobSourceVideo[];
}
