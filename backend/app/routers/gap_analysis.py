"""Phase 6: Gap analysis router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import GapAnalysis, Obligation, PolicyMapping, Workspace
from app.schemas.gap_analysis import GapAnalysisRead, GapAnalysisRunRead
from app.services.gap_analysis import MODEL_NAME, analyse_all_gaps

log = get_logger(__name__)
router = APIRouter(prefix="/workspaces", tags=["gap-analysis"])


@router.post(
    "/{workspace_id}/gap-analysis/run",
    response_model=GapAnalysisRunRead,
    status_code=200,
)
async def run_gap_analysis(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> GapAnalysisRunRead:
    """Assess each obligation against its policy mapping to produce gap results."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    # Load obligations
    obl_result = await db.execute(
        select(Obligation)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(Obligation.created_at, Obligation.id)
    )
    obligations = list(obl_result.scalars().all())
    if not obligations:
        raise HTTPException(
            status_code=400,
            detail="Run obligation extraction before gap analysis.",
        )

    obl_ids = [o.id for o in obligations]

    # Load policy mappings (one per obligation expected)
    mapping_result = await db.execute(
        select(PolicyMapping)
        .where(PolicyMapping.obligation_id.in_(obl_ids))
    )
    mappings = list(mapping_result.scalars().all())
    if not mappings:
        raise HTTPException(
            status_code=400,
            detail="Run policy mapping before gap analysis.",
        )

    # Build obligation → mapping lookup (take first mapping per obligation)
    mapping_by_obl: dict[str, PolicyMapping] = {}
    for m in mappings:
        if m.obligation_id not in mapping_by_obl:
            mapping_by_obl[m.obligation_id] = m

    pairs = [
        (obl, mapping_by_obl[obl.id])
        for obl in obligations
        if obl.id in mapping_by_obl
    ]
    if not pairs:
        raise HTTPException(
            status_code=400,
            detail="No obligation/mapping pairs found. Run policy mapping first.",
        )

    # Delete existing gap analyses for these obligations
    await db.execute(
        delete(GapAnalysis).where(GapAnalysis.obligation_id.in_(obl_ids))
    )

    # Run analysis
    results = await analyse_all_gaps(pairs)
    for r in results:
        db.add(
            GapAnalysis(
                obligation_id=r.obligation_id,
                policy_mapping_id=r.policy_mapping_id,
                coverage_status=r.coverage_status,
                risk_level=r.risk_level,
                reasoning=r.reasoning,
                source_citations=r.source_citations,
                confidence=r.confidence,
                model_name=r.model_name,
            )
        )

    workspace.status = "gap_analysis_run"
    await db.commit()

    # Build summary counts
    fully = sum(1 for r in results if r.coverage_status == "fully_covered")
    partial = sum(1 for r in results if r.coverage_status == "partially_covered")
    not_cov = sum(1 for r in results if r.coverage_status == "not_covered")
    high_risk = sum(1 for r in results if r.risk_level == "high")

    log.info(
        "gap_analysis.run",
        workspace_id=workspace_id,
        total=len(results),
        fully_covered=fully,
        partially_covered=partial,
        not_covered=not_cov,
        high_risk=high_risk,
    )

    return GapAnalysisRunRead(
        workspace_id=workspace_id,
        status="gap_analysis_run",
        obligation_count=len(results),
        fully_covered=fully,
        partially_covered=partial,
        not_covered=not_cov,
        high_risk=high_risk,
        model_name=MODEL_NAME,
    )


@router.get(
    "/{workspace_id}/gap-analysis",
    response_model=list[GapAnalysisRead],
)
async def list_gap_analyses(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[GapAnalysisRead]:
    """Return all gap analysis results for a workspace."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    result = await db.execute(
        select(GapAnalysis)
        .join(Obligation, GapAnalysis.obligation_id == Obligation.id)
        .where(Obligation.workspace_id == workspace_id)
        .order_by(GapAnalysis.created_at, GapAnalysis.id)
    )
    return list(result.scalars().all())
