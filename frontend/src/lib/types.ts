/** Shared TypeScript types for RegLoop AI API responses. */

export type DocumentType =
  | "regulation"
  | "policy"
  | "responsibility_matrix";

export type DocumentStatus = "uploaded" | "ingested" | "failed";

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

export interface DocumentChunkRead {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number: number | null;
  section_label: string | null;
  text: string;
  created_at: string;
}

export interface ResponsibilityOwnerRead {
  id: string;
  workspace_id: string;
  domain: string;
  policy_area: string;
  owner_name: string;
  owner_role: string | null;
  owner_email: string | null;
  notes: string | null;
  created_at: string;
}

export interface IngestionRunRead {
  workspace_id: string;
  status: string;
  document_count: number;
  chunk_count: number;
  owner_count: number;
}

export interface IngestionStatusRead {
  workspace_id: string;
  status: string;
  chunks: DocumentChunkRead[];
  responsibility_owners: ResponsibilityOwnerRead[];
}

export interface ObligationRead {
  id: string;
  workspace_id: string;
  statement: string;
  source_document_id: string;
  source_reference: string;
  source_excerpt: string;
  compliance_domain: string | null;
  confidence: number;
  model_name: string;
  created_at: string;
}

export interface ObligationExtractionRunRead {
  workspace_id: string;
  status: string;
  obligation_count: number;
  model_name: string;
}

export interface PolicyMappingRead {
  id: string;
  obligation_id: string;
  policy_document_id: string | null;
  document_chunk_id: string | null;
  policy_excerpt: string | null;
  mapping_rationale: string;
  confidence: number;
  is_no_match: boolean;
  model_name: string;
  created_at: string;
}

export interface MappingRunRead {
  workspace_id: string;
  status: string;
  obligation_count: number;
  mapping_count: number;
  no_match_count: number;
  model_name: string;
}

export interface GapAnalysisRead {
  id: string;
  obligation_id: string;
  policy_mapping_id: string | null;
  coverage_status: string;
  risk_level: string;
  reasoning: string;
  source_citations: string | null;
  confidence: number;
  model_name: string;
  created_at: string;
}

export interface GapAnalysisRunRead {
  workspace_id: string;
  status: string;
  obligation_count: number;
  fully_covered: number;
  partially_covered: number;
  not_covered: number;
  high_risk: number;
  model_name: string;
}

export interface ApiError {
  detail: string;
  status: number;
}
