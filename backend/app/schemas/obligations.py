"""Pydantic schemas for regulatory obligations."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ObligationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    statement: str
    source_document_id: str
    source_reference: str
    source_excerpt: str
    compliance_domain: str | None
    confidence: int
    model_name: str
    created_at: datetime


class ObligationExtractionRunRead(BaseModel):
    workspace_id: str
    status: str
    obligation_count: int
    model_name: str
