"""Pydantic schemas for document ingestion."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    chunk_index: int
    page_number: int | None
    section_label: str | None
    text: str
    created_at: datetime


class ResponsibilityOwnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    domain: str
    policy_area: str
    owner_name: str
    owner_role: str | None
    owner_email: str | None
    notes: str | None
    created_at: datetime


class IngestionRunRead(BaseModel):
    workspace_id: str
    status: str
    document_count: int
    chunk_count: int
    owner_count: int


class IngestionStatusRead(BaseModel):
    workspace_id: str
    status: str
    chunks: list[DocumentChunkRead]
    responsibility_owners: list[ResponsibilityOwnerRead]
