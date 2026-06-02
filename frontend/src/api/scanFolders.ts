import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type { ScanFolder, ScanStatus } from "./types";

export function listScanFolders() {
  return apiGet<{ items: ScanFolder[] }>("/api/scan-folders");
}

export function pickFolder() {
  return apiPost<{ path: string } | undefined>("/api/system/pick-folder");
}

export function createScanFolder(path: string) {
  return apiPost<ScanFolder>("/api/scan-folders", { path });
}

export function updateScanFolder(id: number, enabled: boolean) {
  return apiPatch<ScanFolder>(`/api/scan-folders/${id}`, { enabled });
}

export function deleteScanFolder(id: number, deleteVideos: boolean) {
  return apiDelete(`/api/scan-folders/${id}?delete_videos=${deleteVideos}`);
}

export function scanFolder(id: number) {
  return apiPost(`/api/scan-folders/${id}/scan`);
}

export function resyncMetadata(id: number) {
  return apiPost(`/api/scan-folders/${id}/resync-metadata`);
}

export function scanAllFolders() {
  return apiPost("/api/scan-folders/scan-all");
}

export function getScanStatus(id: number) {
  return apiGet<ScanStatus>(`/api/scan-folders/${id}/status`);
}
