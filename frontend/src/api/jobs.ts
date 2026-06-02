import { apiGet, apiPost } from "./client";
import type { JobSummary, Paginated } from "./types";

export interface JobListParams {
  page?: number;
  page_size?: number;
  type?: string;
  status?: string;
}

export function listJobs(params: JobListParams = {}) {
  const q = new URLSearchParams();
  if (params.page) q.set("page", String(params.page));
  if (params.page_size) q.set("page_size", String(params.page_size));
  if (params.type) q.set("type", params.type);
  if (params.status) q.set("status", params.status);
  const qs = q.toString();
  return apiGet<Paginated<JobSummary>>(`/api/jobs${qs ? `?${qs}` : ""}`);
}

export function retryJob(id: number) {
  return apiPost<{ job_id: number; type: string; status: string }>(`/api/jobs/${id}/retry`);
}
