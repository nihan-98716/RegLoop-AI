"""Workspaces and documents router."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import Document, Workspace
from app.schemas.workspace import (
    DocumentRead,
    WorkspaceCreate,
    WorkspaceDetailRead,
    WorkspaceRead,
)
from app.services.upload import (
    delete_stored_file,
    is_ready_for_analysis,
    save_upload,
    validate_count_rules,
    validate_document_type,
    validate_file_extension,
)

log = get_logger(__name__)
router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_workspace_or_404(workspace_id: str, db: AsyncSession) -> Workspace:
    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")
    return ws


async def _workspace_detail(workspace: Workspace, db: AsyncSession) -> WorkspaceDetailRead:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace.id)
        .order_by(Document.created_at)
    )
    docs = result.scalars().all()
    return WorkspaceDetailRead(
        id=workspace.id,
        name=workspace.name,
        status=workspace.status,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        documents=[DocumentRead.model_validate(d) for d in docs],
        ready_for_analysis=is_ready_for_analysis(docs),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    body: WorkspaceCreate | None = None,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceRead:
    """Create a new compliance review workspace."""
    if body is None:
        body = WorkspaceCreate()
    name = body.name or f"Compliance Review {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC"
    workspace = Workspace(id=str(uuid.uuid4()), name=name)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    log.info("workspace.created", workspace_id=workspace.id, name=workspace.name)
    return WorkspaceRead.model_validate(workspace)


@router.get("/{workspace_id}", response_model=WorkspaceDetailRead)
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceDetailRead:
    """Return workspace metadata, document list, and analysis readiness."""
    workspace = await _get_workspace_or_404(workspace_id, db)
    return await _workspace_detail(workspace, db)


@router.post("/{workspace_id}/documents", response_model=DocumentRead, status_code=201)
async def upload_document(
    workspace_id: str,
    document_type: str = Form(..., description="regulation | policy | responsibility_matrix"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Upload a document to a workspace."""
    workspace = await _get_workspace_or_404(workspace_id, db)

    # Validate inputs
    validate_document_type(document_type)
    validate_file_extension(file, document_type)

    # Enforce count rules
    result = await db.execute(
        select(Document.document_type).where(Document.workspace_id == workspace_id)
    )
    existing_types = list(result.scalars().all())
    validate_count_rules(existing_types, document_type)

    # Persist file
    document_id = str(uuid.uuid4())
    storage_path, size_bytes, checksum = await save_upload(file, workspace_id, document_id)

    doc = Document(
        id=document_id,
        workspace_id=workspace_id,
        document_type=document_type,
        filename=f"{document_id}_{file.filename or 'file'}",
        original_filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        storage_path=storage_path,
        size_bytes=size_bytes,
        checksum=checksum,
        status="uploaded",
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    log.info(
        "document.uploaded",
        doc_id=doc.id,
        type=document_type,
        filename=file.filename,
        size=size_bytes,
    )
    return DocumentRead.model_validate(doc)


@router.delete("/{workspace_id}/documents/{document_id}", status_code=204)
async def delete_document(
    workspace_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a document and its stored file from a workspace."""
    await _get_workspace_or_404(workspace_id, db)

    doc = await db.get(Document, document_id)
    if not doc or doc.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Document not found in this workspace.")

    delete_stored_file(doc.storage_path)
    await db.delete(doc)
    await db.commit()
    log.info("document.deleted", doc_id=document_id)
