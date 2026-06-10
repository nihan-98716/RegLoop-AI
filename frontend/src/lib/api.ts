/**
 * RegLoop AI — typed API client.
 * Thin fetch wrapper with error handling and multipart upload support.
 */

import type {
  DocumentRead,
  DocumentType,
  GapAnalysisRead,
  GapAnalysisRunRead,
  IngestionRunRead,
  IngestionStatusRead,
  MappingRunRead,
  ObligationExtractionRunRead,
  ObligationRead,
  PolicyMappingRead,
  WorkspaceDetailRead,
  WorkspaceRead,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

// ── Core fetch ────────────────────────────────────────────────────────────────

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
    ...options,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch { /* ignore */ }
    throw { detail, status: res.status };
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

async function uploadForm<T>(path: string, form: FormData): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, { method: "POST", body: form });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch { /* ignore */ }
    throw { detail, status: res.status };
  }
  return res.json() as Promise<T>;
}

// ── API surface ───────────────────────────────────────────────────────────────

export const api = {
  /** GET /health */
  health(): Promise<{ status: string; database: string }> {
    return request("/health");
  },

  workspace: {
    /** POST /workspaces */
    create(name?: string): Promise<WorkspaceRead> {
      return request("/workspaces", {
        method: "POST",
        body: JSON.stringify({ name: name ?? null }),
      });
    },

    /** GET /workspaces/{id} */
    get(id: string): Promise<WorkspaceDetailRead> {
      return request(`/workspaces/${id}`);
    },

    /** POST /workspaces/{id}/documents */
    uploadDocument(
      workspaceId: string,
      file: File,
      documentType: DocumentType,
    ): Promise<DocumentRead> {
      const form = new FormData();
      form.append("document_type", documentType);
      form.append("file", file);
      return uploadForm(`/workspaces/${workspaceId}/documents`, form);
    },

    /** DELETE /workspaces/{id}/documents/{docId} */
    deleteDocument(workspaceId: string, docId: string): Promise<void> {
      return request(`/workspaces/${workspaceId}/documents/${docId}`, {
        method: "DELETE",
      });
    },

    /** POST /workspaces/{id}/ingestion */
    runIngestion(workspaceId: string): Promise<IngestionRunRead> {
      return request(`/workspaces/${workspaceId}/ingestion`, {
        method: "POST",
      });
    },

    /** GET /workspaces/{id}/ingestion */
    getIngestion(workspaceId: string): Promise<IngestionStatusRead> {
      return request(`/workspaces/${workspaceId}/ingestion`);
    },

    /** POST /workspaces/{id}/obligations/extract */
    extractObligations(workspaceId: string): Promise<ObligationExtractionRunRead> {
      return request(`/workspaces/${workspaceId}/obligations/extract`, {
        method: "POST",
      });
    },

    /** GET /workspaces/{id}/obligations */
    listObligations(workspaceId: string): Promise<ObligationRead[]> {
      return request(`/workspaces/${workspaceId}/obligations`);
    },

    /** POST /workspaces/{id}/mappings/run */
    runMapping(workspaceId: string): Promise<MappingRunRead> {
      return request(`/workspaces/${workspaceId}/mappings/run`, {
        method: "POST",
      });
    },

    /** GET /workspaces/{id}/mappings */
    listMappings(workspaceId: string): Promise<PolicyMappingRead[]> {
      return request(`/workspaces/${workspaceId}/mappings`);
    },

    /** POST /workspaces/{id}/gap-analysis/run */
    runGapAnalysis(workspaceId: string): Promise<GapAnalysisRunRead> {
      return request(`/workspaces/${workspaceId}/gap-analysis/run`, {
        method: "POST",
      });
    },

    /** GET /workspaces/{id}/gap-analysis */
    listGapAnalyses(workspaceId: string): Promise<GapAnalysisRead[]> {
      return request(`/workspaces/${workspaceId}/gap-analysis`);
    },
  },
} as const;

export default api;
