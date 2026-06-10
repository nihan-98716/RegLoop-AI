"""Document ingestion routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import Document, DocumentChunk, ResponsibilityOwner, Workspace
from app.schemas.ingestion import IngestionRunRead, IngestionStatusRead
from app.services.ingestion import chunk_pdf_document, parse_responsibility_matrix
from app.services.upload import is_ready_for_analysis

log = get_logger(__name__)
router = APIRouter(prefix="/workspaces", tags=["ingestion"])


@router.post("/{workspace_id}/ingestion", response_model=IngestionRunRead)
async def run_ingestion(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> IngestionRunRead:
    """Extract PDF text chunks and responsibility owners for a ready workspace."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    documents = await _workspace_documents(workspace_id, db)
    if not is_ready_for_analysis(documents):
        raise HTTPException(
            status_code=400,
            detail="Workspace must include one regulation PDF, one to three policy PDFs, and one responsibility matrix CSV before ingestion.",
        )

    await _clear_previous_ingestion(workspace_id, documents, db)

    chunk_count = 0
    owner_count = 0
    try:
        for doc in documents:
            if doc.document_type in {"regulation", "policy"}:
                parsed_chunks = chunk_pdf_document(
                    doc.storage_path,
                    is_policy=doc.document_type == "policy",
                )
                for parsed in parsed_chunks:
                    db.add(
                        DocumentChunk(
                            document_id=doc.id,
                            chunk_index=parsed.chunk_index,
                            page_number=parsed.page_number,
                            section_label=parsed.section_label,
                            text=parsed.text,
                        )
                    )
                chunk_count += len(parsed_chunks)
                doc.status = "ingested"
            elif doc.document_type == "responsibility_matrix":
                parsed_owners = parse_responsibility_matrix(doc.storage_path)
                for parsed in parsed_owners:
                    db.add(
                        ResponsibilityOwner(
                            workspace_id=workspace_id,
                            domain=parsed.domain,
                            policy_area=parsed.policy_area,
                            owner_name=parsed.owner_name,
                            owner_role=parsed.owner_role,
                            owner_email=parsed.owner_email,
                            notes=parsed.notes,
                        )
                    )
                owner_count += len(parsed_owners)
                doc.status = "ingested"

        workspace.status = "ingested"
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    log.info(
        "ingestion.completed",
        workspace_id=workspace_id,
        chunks=chunk_count,
        owners=owner_count,
    )
    return IngestionRunRead(
        workspace_id=workspace_id,
        status="ingested",
        document_count=len(documents),
        chunk_count=chunk_count,
        owner_count=owner_count,
    )


@router.get("/{workspace_id}/ingestion", response_model=IngestionStatusRead)
async def get_ingestion(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> IngestionStatusRead:
    """Return normalized chunks and responsibility owners for a workspace."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    documents = await _workspace_documents(workspace_id, db)
    document_ids = [doc.id for doc in documents]

    if document_ids:
        chunk_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
        )
        chunks = list(chunk_result.scalars().all())
    else:
        chunks = []

    owner_result = await db.execute(
        select(ResponsibilityOwner)
        .where(ResponsibilityOwner.workspace_id == workspace_id)
        .order_by(ResponsibilityOwner.domain, ResponsibilityOwner.policy_area)
    )
    owners = list(owner_result.scalars().all())

    return IngestionStatusRead(
        workspace_id=workspace_id,
        status=workspace.status,
        chunks=chunks,
        responsibility_owners=owners,
    )


async def _workspace_documents(workspace_id: str, db: AsyncSession) -> list[Document]:
    result = await db.execute(
        select(Document).where(Document.workspace_id == workspace_id).order_by(Document.created_at)
    )
    return list(result.scalars().all())


async def _clear_previous_ingestion(
    workspace_id: str,
    documents: list[Document],
    db: AsyncSession,
) -> None:
    document_ids = [doc.id for doc in documents]
    if document_ids:
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(document_ids)))
    await db.execute(
        delete(ResponsibilityOwner).where(ResponsibilityOwner.workspace_id == workspace_id)
    )
