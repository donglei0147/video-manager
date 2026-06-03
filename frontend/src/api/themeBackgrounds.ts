import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { Paginated } from "./types";

export interface ThemeBackground {
  id: number;
  name: string;
  image_url: string;
  source_video_id: number | null;
  source_time_sec: number | null;
  width: number | null;
  height: number | null;
  video_count: number;
  created_at: string;
  updated_at: string;
}

export interface ThemeBackgroundListParams {
  page?: number;
  page_size?: number;
  keyword?: string;
}

export function listThemeBackgrounds(params: ThemeBackgroundListParams = {}) {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.keyword) q.set("keyword", params.keyword);
  const qs = q.toString();
  return apiGet<Paginated<ThemeBackground>>(`/api/theme-backgrounds${qs ? `?${qs}` : ""}`);
}

export function getThemeBackground(id: number) {
  return apiGet<ThemeBackground>(`/api/theme-backgrounds/${id}`);
}

export function updateThemeBackground(id: number, name: string) {
  return apiPatch<ThemeBackground>(`/api/theme-backgrounds/${id}`, { name });
}

export function deleteThemeBackground(id: number) {
  return apiDelete(`/api/theme-backgrounds/${id}`);
}

export function createThemeBackgroundFromFrame(
  videoId: number,
  body: { time_sec: number; name?: string | null }
) {
  return apiPost<ThemeBackground>(`/api/videos/${videoId}/theme-backgrounds/from-frame`, body);
}

export function linkThemeBackground(videoId: number, backgroundId: number) {
  return apiPost<import("./videos").VideoDetail>(
    `/api/videos/${videoId}/theme-backgrounds/${backgroundId}/link`
  );
}

export function unlinkThemeBackground(videoId: number) {
  return apiDelete(`/api/videos/${videoId}/theme-background`);
}
