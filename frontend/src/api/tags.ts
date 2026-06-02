import { apiGet, apiPost } from "./client";

export interface TagItem {
  id: number;
  name: string;
}

export function listTags(q?: string, limit = 20) {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  params.set("limit", String(limit));
  const qs = params.toString();
  return apiGet<{ items: TagItem[] }>(`/api/tags?${qs}`);
}

export function createTag(name: string) {
  return apiPost<TagItem>("/api/tags", { name });
}
