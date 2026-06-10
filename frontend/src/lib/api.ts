/**
 * RegLoop AI — API client helper.
 *
 * A thin typed wrapper around fetch for all backend API calls.
 * The base URL is read from NEXT_PUBLIC_API_URL (set in .env.local or Docker).
 *
 * Usage:
 *   import { api } from "@/lib/api";
 *   const health = await api.health();
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

// ── Types ────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status: "ok" | "error";
  database: "ok" | "error";
}

export interface ApiError {
  detail: string;
  status: number;
}

// ── Core fetch wrapper ───────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;

  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse errors — keep the HTTP status message
    }
    const err: ApiError = { detail, status: response.status };
    throw err;
  }

  // 204 No Content
  if (response.status === 204) {
    return undefined as unknown as T;
  }

  return response.json() as Promise<T>;
}

// Multipart / file upload variant (no Content-Type header — browser sets boundary)
async function upload<T>(path: string, body: FormData): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const response = await fetch(url, { method: "POST", body });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const b = await response.json();
      detail = b?.detail ?? detail;
    } catch {
      // ignore
    }
    const err: ApiError = { detail, status: response.status };
    throw err;
  }

  return response.json() as Promise<T>;
}

// ── API surface ──────────────────────────────────────────────────────────────

export const api = {
  /** GET /health — backend liveness + database check */
  health(): Promise<HealthResponse> {
    return request<HealthResponse>("/health");
  },
} as const;

export default api;
