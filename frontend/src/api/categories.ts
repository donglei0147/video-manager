import { apiGet, apiPost, apiDelete } from "./client";

export interface Category {
  id: number;
  name: string;
  sort_order: number;
  video_count: number;
}

export function listCategories() {
  return apiGet<{ items: Category[] }>("/api/categories");
}

export function createCategory(name: string, sort_order = 0) {
  return apiPost<Category>("/api/categories", { name, sort_order });
}

export function deleteCategory(id: number) {
  return apiDelete(`/api/categories/${id}`);
}
