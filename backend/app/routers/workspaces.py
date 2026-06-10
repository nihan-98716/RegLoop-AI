"""Workspaces and documents router."""

import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import (
    Document,
    GapAnalysis,
    Obligation,
    PolicyMapping,
    PolicyPullRequest,
    Workspace,
)
from app.schemas.gap_analysis import GapAnalysisRead
from app.schemas.mapping import PolicyMappingRead
from app.schemas.obligations import ObligationRead
from app.schemas.pull_request import PolicyPullRequestRead
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


@router.get("/{workspace_id}/export.json")
async def export_workspace_json(
    workspace_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Download full workspace compliance review package as JSON."""
    workspace = await _get_workspace_or_404(workspace_id, db)

    # 1. Documents
    doc_res = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id).order_by(Document.created_at)
    )
    documents = list(doc_res.scalars().all())

    # 2. Obligations
    obl_res = await db.execute(
        select(Obligation)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(Obligation.created_at, Obligation.id)
    )
    obligations = list(obl_res.scalars().all())
    obl_ids = [o.id for o in obligations]

    # 3. Mappings
    mappings = []
    if obl_ids:
        map_res = await db.execute(
            select(PolicyMapping)
            .where(PolicyMapping.obligation_id.in_(obl_ids))
            .order_by(PolicyMapping.created_at, PolicyMapping.id)
        )
        mappings = list(map_res.scalars().all())

    # 4. Gap analyses
    gaps = []
    if obl_ids:
        gap_res = await db.execute(
            select(GapAnalysis)
            .where(GapAnalysis.obligation_id.in_(obl_ids))
            .order_by(GapAnalysis.created_at, GapAnalysis.id)
        )
        gaps = list(gap_res.scalars().all())

    # 5. Pull requests
    prs = []
    if obl_ids:
        pr_res = await db.execute(
            select(PolicyPullRequest)
            .where(PolicyPullRequest.obligation_id.in_(obl_ids))
            .options(
                selectinload(PolicyPullRequest.suggested_owner),
                selectinload(PolicyPullRequest.review_actions),
            )
            .order_by(PolicyPullRequest.created_at, PolicyPullRequest.id)
        )
        prs = list(pr_res.scalars().all())

    data = {
        "workspace": WorkspaceRead.model_validate(workspace).model_dump(),
        "documents": [DocumentRead.model_validate(d).model_dump() for d in documents],
        "obligations": [ObligationRead.model_validate(o).model_dump() for o in obligations],
        "policy_mappings": [PolicyMappingRead.model_validate(m).model_dump() for m in mappings],
        "gap_analyses": [GapAnalysisRead.model_validate(g).model_dump() for g in gaps],
        "policy_pull_requests": [
            PolicyPullRequestRead.model_validate(pr).model_dump() for pr in prs
        ],
    }

    response.headers["Content-Disposition"] = f"attachment; filename=workspace_{workspace_id}_export.json"
    return data


@router.get("/{workspace_id}/export.csv")
async def export_workspace_csv(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Download a flattened CSV export suitable for spreadsheet review."""
    workspace = await _get_workspace_or_404(workspace_id, db)

    # Load all models for workspace
    doc_res = await db.execute(select(Document).where(Document.workspace_id == workspace_id))
    obligations_res = await db.execute(
        select(Obligation)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(Obligation.created_at, Obligation.id)
    )
    obligations = list(obligations_res.scalars().all())
    obl_ids = [o.id for o in obligations]

    mappings = []
    gaps = []
    prs = []

    if obl_ids:
        map_res = await db.execute(select(PolicyMapping).where(PolicyMapping.obligation_id.in_(obl_ids)))
        mappings = list(map_res.scalars().all())

        gap_res = await db.execute(select(GapAnalysis).where(GapAnalysis.obligation_id.in_(obl_ids)))
        gaps = list(gap_res.scalars().all())

        pr_res = await db.execute(
            select(PolicyPullRequest)
            .where(PolicyPullRequest.obligation_id.in_(obl_ids))
            .options(
                selectinload(PolicyPullRequest.suggested_owner),
                selectinload(PolicyPullRequest.review_actions),
            )
        )
        prs = list(pr_res.scalars().all())

    # Map them for easy lookup by obligation_id
    mapping_by_obl = {m.obligation_id: m for m in mappings}
    gap_by_obl = {g.obligation_id: g for g in gaps}
    pr_by_obl = {p.obligation_id: p for p in prs}

    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Write headers
    headers = [
        "Obligation ID",
        "Obligation Statement",
        "Source Reference",
        "Compliance Domain",
        "Obligation Confidence",
        "Mapped Policy Excerpt",
        "Mapping Confidence",
        "Coverage Status",
        "Gap Reasoning",
        "Risk Level",
        "Gap Analysis Confidence",
        "Proposed Policy Amendment",
        "Suggested Owner Name",
        "Suggested Owner Email",
        "PR Status",
        "Latest Reviewer Action",
        "Latest Reviewer Comment",
    ]
    writer.writerow(headers)

    for obl in obligations:
        m = mapping_by_obl.get(obl.id)
        g = gap_by_obl.get(obl.id)
        p = pr_by_obl.get(obl.id)

        latest_action = ""
        latest_comment = ""
        if p and p.review_actions:
            # Sort review actions by created_at to find the latest
            sorted_actions = sorted(p.review_actions, key=lambda a: a.created_at)
            latest_action = sorted_actions[-1].action
            latest_comment = sorted_actions[-1].comment or ""

        row = [
            obl.id,
            obl.statement,
            obl.source_reference,
            obl.compliance_domain or "",
            obl.confidence,
            m.policy_excerpt if (m and not m.is_no_match) else "",
            m.confidence if m else "",
            g.coverage_status if g else "",
            g.reasoning if g else "",
            g.risk_level if g else "",
            g.confidence if g else "",
            p.proposed_amendment if p else "",
            p.suggested_owner.owner_name if (p and p.suggested_owner) else "",
            p.suggested_owner.owner_email if (p and p.suggested_owner) else "",
            p.status if p else "",
            latest_action,
            latest_comment,
        ]
        writer.writerow(row)

    # Reset buffer position
    output.seek(0)

    headers = {
        "Content-Disposition": f"attachment; filename=workspace_{workspace_id}_export.csv"
    }
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers=headers,
    )
