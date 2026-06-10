"""Pydantic schemas for workspaces and documents."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkspaceCreate(BaseModel):
    name: str | None = None


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    document_type: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum: str
    status: str
    created_at: datetime


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class WorkspaceDetailRead(WorkspaceRead):
    documents: list[DocumentRead] = []
    ready_for_analysis: bool = False
