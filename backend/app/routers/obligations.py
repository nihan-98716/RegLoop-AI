"""Regulatory obligation extraction routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import Document, DocumentChunk, Obligation, Workspace
from app.schemas.obligations import ObligationExtractionRunRead, ObligationRead
from app.services.obligations import extract_obligations_from_chunks

log = get_logger(__name__)
router = APIRouter(prefix="/workspaces", tags=["obligations"])


@router.post("/{workspace_id}/obligations/extract", response_model=ObligationExtractionRunRead)
async def extract_obligations(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> ObligationExtractionRunRead:
    """Extract structured obligations from ingested regulatory chunks."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    regulation = await _regulation_document(workspace_id, db)
    if not regulation:
        raise HTTPException(status_code=400, detail="Workspace has no regulation document.")

    chunks = await _regulation_chunks(regulation.id, db)
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="Run document ingestion before extracting obligations.",
        )

    extracted, model_name = extract_obligations_from_chunks(chunks)
    if not extracted:
        raise HTTPException(
            status_code=422,
            detail="No regulatory obligations could be extracted from the regulation.",
        )

    await db.execute(delete(Obligation).where(Obligation.workspace_id == workspace_id))
    for item in extracted:
        db.add(
            Obligation(
                workspace_id=workspace_id,
                statement=item.statement,
                source_document_id=regulation.id,
                source_reference=item.source_reference,
                source_excerpt=item.source_excerpt,
                compliance_domain=item.compliance_domain,
                confidence=item.confidence,
                model_name=model_name,
            )
        )

    workspace.status = "obligations_extracted"
    await db.commit()

    log.info(
        "obligations.extracted",
        workspace_id=workspace_id,
        count=len(extracted),
        model=model_name,
    )
    return ObligationExtractionRunRead(
        workspace_id=workspace_id,
        status="obligations_extracted",
        obligation_count=len(extracted),
        model_name=model_name,
    )


@router.get("/{workspace_id}/obligations", response_model=list[ObligationRead])
async def list_obligations(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[ObligationRead]:
    """Return extracted obligations for a workspace."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    result = await db.execute(
        select(Obligation)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(Obligation.created_at, Obligation.id)
    )
    return list(result.scalars().all())


async def _regulation_document(workspace_id: str, db: AsyncSession) -> Document | None:
    result = await db.execute(
        select(Document)
        .where(Document.workspace_id == workspace_id, Document.document_type == "regulation")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _regulation_chunks(document_id: str, db: AsyncSession) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())
