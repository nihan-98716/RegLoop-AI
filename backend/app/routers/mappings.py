"""Phase 5: Policy mapping router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import (
    Document,
    DocumentChunk,
    Obligation,
    PolicyMapping,
    Workspace,
)
from app.schemas.mapping import MappingRunRead, PolicyMappingRead
from app.services.mapping import map_all_obligations

log = get_logger(__name__)
router = APIRouter(prefix="/workspaces", tags=["mappings"])


@router.post(
    "/{workspace_id}/mappings/run",
    response_model=MappingRunRead,
    status_code=200,
)
async def run_policy_mapping(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> MappingRunRead:
    """Map every obligation in the workspace to the best matching policy section."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    # Require obligations to exist
    obligation_result = await db.execute(
        select(Obligation)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(Obligation.created_at, Obligation.id)
    )
    obligations = list(obligation_result.scalars().all())
    if not obligations:
        raise HTTPException(
            status_code=400,
            detail="Run obligation extraction before policy mapping.",
        )

    # Load all policy chunks
    policy_doc_result = await db.execute(
        select(Document).where(
            Document.workspace_id == workspace_id,
            Document.document_type == "policy",
        )
    )
    policy_docs = list(policy_doc_result.scalars().all())
    policy_doc_ids = {doc.id for doc in policy_docs}

    chunk_result = await db.execute(
        select(DocumentChunk).where(
            DocumentChunk.document_id.in_(policy_doc_ids)
        ).order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
    )
    policy_chunks = list(chunk_result.scalars().all())

    if not policy_chunks:
        raise HTTPException(
            status_code=400,
            detail="No policy document chunks found. Run ingestion before mapping.",
        )

    # Build chunk → document mapping
    chunk_to_doc_id = {chunk.id: chunk.document_id for chunk in policy_chunks}

    # Delete existing mappings for this workspace
    await db.execute(
        delete(PolicyMapping).where(
            PolicyMapping.obligation_id.in_([o.id for o in obligations])
        )
    )

    # Run mapping
    validated_mappings = map_all_obligations(obligations, policy_chunks, chunk_to_doc_id)

    for vm in validated_mappings:
        db.add(
            PolicyMapping(
                obligation_id=vm.obligation_id,
                policy_document_id=vm.policy_document_id,
                document_chunk_id=vm.document_chunk_id,
                policy_excerpt=vm.policy_excerpt,
                mapping_rationale=vm.mapping_rationale,
                confidence=vm.confidence,
                is_no_match=vm.is_no_match,
                model_name=vm.model_name,
            )
        )

    workspace.status = "mappings_run"
    await db.commit()

    no_match_count = sum(1 for vm in validated_mappings if vm.is_no_match)
    log.info(
        "mappings.run",
        workspace_id=workspace_id,
        total=len(validated_mappings),
        no_match=no_match_count,
    )
    return MappingRunRead(
        workspace_id=workspace_id,
        status="mappings_run",
        obligation_count=len(obligations),
        mapping_count=len(validated_mappings),
        no_match_count=no_match_count,
        model_name=validated_mappings[0].model_name if validated_mappings else "n/a",
    )


@router.get(
    "/{workspace_id}/mappings",
    response_model=list[PolicyMappingRead],
)
async def list_policy_mappings(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[PolicyMappingRead]:
    """Return all policy mappings for a workspace."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    result = await db.execute(
        select(PolicyMapping)
        .join(Obligation, PolicyMapping.obligation_id == Obligation.id)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(PolicyMapping.created_at, PolicyMapping.id)
    )
    return list(result.scalars().all())
