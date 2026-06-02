export class ApiError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

const ENV_API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? "";
const API_BASE = ENV_API_BASE.replace(/\/+$/, "");
const DEFAULT_API_BASE = "http://127.0.0.1:8765";

function resolveUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  if (API_BASE) return `${API_BASE}${path}`;

  // In non-dev serving mode (e.g. static hosting), relative /api may hit a wrong service.
  if (typeof window !== "undefined" && window.location.port !== "5173") {
    return `${DEFAULT_API_BASE}${path}`;
  }
  return path;
}

async function parseError(res: Response): Promise<never> {
  const data = await res.json().catch(() => ({}));
  const err = data?.error;
  throw new ApiError(err?.code ?? "HTTP_ERROR", err?.message ?? res.statusText);
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(resolveUrl(path));
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(resolveUrl(path), {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 204) return undefined as T;
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(resolveUrl(path), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) await parseError(res);
  return res.json();
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(resolveUrl(path), { method: "DELETE" });
  if (!res.ok && res.status !== 204) await parseError(res);
}
