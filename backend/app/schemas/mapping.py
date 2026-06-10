"""Pydantic schemas for policy mappings."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PolicyMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    obligation_id: str
    policy_document_id: str | None
    document_chunk_id: str | None
    policy_excerpt: str | None
    mapping_rationale: str
    confidence: int
    is_no_match: bool
    model_name: str
    created_at: datetime


class MappingRunRead(BaseModel):
    workspace_id: str
    status: str
    obligation_count: int
    mapping_count: int
    no_match_count: int
    model_name: str
