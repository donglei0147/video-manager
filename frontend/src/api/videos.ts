import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { Paginated, VideoSummary } from "./types";

export interface VideoListParams {
  page?: number;
  page_size?: number;
  include_missing?: boolean;
  sort?: string;
  category_id?: number;
  tag_ids?: number[];
  q?: string;
  record_start_from?: string;
  record_start_to?: string;
  record_end_from?: string;
  record_end_to?: string;
  has_record_time?: boolean;
  favorite_min?: number;
  theme_background_id?: number;
}

export interface VideoDetail extends VideoSummary {
  scan_folder_id: number;
  file_path: string;
  video_codec: string | null;
  audio_codec: string | null;
  indexed_at: string;
  updated_at: string;
}

export interface JobEnqueueResponse {
  job_id: number;
  type: string;
  status: string;
}

export interface MergePreflightResponse {
  ok: boolean;
  video_ids: number[];
}

export function listVideos(params: VideoListParams = {}) {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.include_missing) q.set("include_missing", "true");
  if (params.sort) q.set("sort", params.sort);
  if (params.category_id != null) q.set("category_id", String(params.category_id));
  if (params.tag_ids?.length) q.set("tag_ids", params.tag_ids.join(","));
  if (params.q) q.set("q", params.q);
  if (params.record_start_from) q.set("record_start_from", params.record_start_from);
  if (params.record_start_to) q.set("record_start_to", params.record_start_to);
  if (params.record_end_from) q.set("record_end_from", params.record_end_from);
  if (params.record_end_to) q.set("record_end_to", params.record_end_to);
  if (params.has_record_time === true) q.set("has_record_time", "true");
  if (params.has_record_time === false) q.set("has_record_time", "false");
  if (params.favorite_min != null) q.set("favorite_min", String(params.favorite_min));
  if (params.theme_background_id != null) {
    q.set("theme_background_id", String(params.theme_background_id));
  }
  const qs = q.toString();
  return apiGet<Paginated<VideoSummary>>(`/api/videos${qs ? `?${qs}` : ""}`);
}

export function getVideo(id: number) {
  return apiGet<VideoDetail>(`/api/videos/${id}`);
}

export function updateVideo(id: number, body: Record<string, unknown>) {
  return apiPatch<VideoDetail>(`/api/videos/${id}`, body);
}

export function openVideoFolder(id: number) {
  return apiPost<void>(`/api/videos/${id}/open-folder`);
}

export function deleteVideo(id: number) {
  return apiDelete(`/api/videos/${id}`);
}

export function createVideoClip(body: {
  video_id: number;
  start_sec: number;
  end_sec?: number;
  output_file_name?: string;
}) {
  return apiPost<JobEnqueueResponse>("/api/jobs/video-clip", body);
}

export function mergeVideosPreflight(videoIds: number[]) {
  return apiPost<MergePreflightResponse>("/api/jobs/merge-videos/preflight", { video_ids: videoIds });
}

export function createMergeVideos(body: { video_ids: number[]; output_file_name?: string }) {
  return apiPost<JobEnqueueResponse>("/api/jobs/merge-videos", body);
}
