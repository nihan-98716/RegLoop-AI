/** Shared TypeScript types for RegLoop AI API responses. */

export type DocumentType =
  | "regulation"
  | "policy"
  | "responsibility_matrix";

export type DocumentStatus = "uploaded" | "failed";

export interface DocumentRead {
  id: string;
  workspace_id: string;
  document_type: DocumentType;
  filename: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  checksum: string;
  status: DocumentStatus;
  created_at: string;
}

export interface WorkspaceRead {
  id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceDetailRead extends WorkspaceRead {
  documents: DocumentRead[];
  ready_for_analysis: boolean;
}

export interface ApiError {
  detail: string;
  status: number;
}
