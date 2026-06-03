import { ApiError, apiDelete, apiGet, apiPost } from "./client";

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

export function deleteTag(id: number) {
  return apiDelete(`/api/tags/${id}`);
}

/** 创建标签；若名称已存在则返回已有标签 */
export async function getOrCreateTag(name: string): Promise<TagItem> {
  const trimmed = name.trim();
  if (!trimmed) {
    throw new Error("标签名称不能为空");
  }
  try {
    return await createTag(trimmed);
  } catch (e) {
    if (e instanceof ApiError && e.code === "CONFLICT") {
      const res = await listTags(trimmed, 100);
      const existing = res.items.find((t) => t.name === trimmed);
      if (existing) return existing;
    }
    throw e;
  }
}
