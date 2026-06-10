"""Phase 7: Policy Pull Requests router."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.logging_config import get_logger
from app.models.workspace import (
    GapAnalysis,
    Obligation,
    PolicyMapping,
    PolicyPullRequest,
    ResponsibilityOwner,
    ReviewAction,
    Workspace,
)
from app.schemas.pull_request import (
    PolicyPullRequestRead,
    PolicyPullRequestRunRead,
    ReviewActionCreate,
)
from app.services.pull_request import MODEL_NAME, generate_pr_for_gap

log = get_logger(__name__)
router = APIRouter(tags=["policy-pull-requests"])


@router.post(
    "/workspaces/{workspace_id}/policy-pull-requests/run",
    response_model=PolicyPullRequestRunRead,
    status_code=200,
)
async def run_policy_pull_requests(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
) -> PolicyPullRequestRunRead:
    """Generate policy pull requests/amendments for obligations with coverage gaps."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    # Load gap analyses
    gap_result = await db.execute(
        select(GapAnalysis)
        .join(Obligation, GapAnalysis.obligation_id == Obligation.id)
        .where(Obligation.workspace_id == workspace_id)
    )
    gaps = list(gap_result.scalars().all())
    if not gaps:
        raise HTTPException(
            status_code=400,
            detail="Run gap analysis before generating policy pull requests.",
        )

    # Load responsibility owners
    owner_result = await db.execute(
        select(ResponsibilityOwner).where(ResponsibilityOwner.workspace_id == workspace_id)
    )
    owners = list(owner_result.scalars().all())

    # Load obligations and mappings
    obl_result = await db.execute(
        select(Obligation).where(Obligation.workspace_id == workspace_id)
    )
    obligations = {o.id: o for o in obl_result.scalars().all()}

    mapping_result = await db.execute(
        select(PolicyMapping)
        .join(Obligation, PolicyMapping.obligation_id == Obligation.id)
        .where(Obligation.workspace_id == workspace_id)
    )
    mappings = {m.obligation_id: m for m in mapping_result.scalars().all()}

    # Clear existing pull requests (ReviewActions will delete via CASCADE)
    await db.execute(
        delete(PolicyPullRequest).where(PolicyPullRequest.workspace_id == workspace_id)
    )

    # Generate PRs only for gaps (partially_covered or not_covered)
    gaps_to_amend = [g for g in gaps if g.coverage_status in ("partially_covered", "not_covered")]
    generated_prs = []

    for gap in gaps_to_amend:
        obl = obligations.get(gap.obligation_id)
        if not obl:
            continue
        mapping = mappings.get(gap.obligation_id)
        pr_data = await generate_pr_for_gap(obl, gap, mapping, owners)

        db_pr = PolicyPullRequest(
            workspace_id=workspace_id,
            obligation_id=pr_data.obligation_id,
            gap_analysis_id=pr_data.gap_analysis_id,
            title=pr_data.title,
            gap_description=pr_data.gap_description,
            proposed_amendment=pr_data.proposed_amendment,
            regulatory_citation=pr_data.regulatory_citation,
            suggested_owner_id=pr_data.suggested_owner_id,
            risk_level=pr_data.risk_level,
            confidence=pr_data.confidence,
            before_text=pr_data.before_text,
            after_text=pr_data.after_text,
            status=pr_data.status,
        )
        db.add(db_pr)
        generated_prs.append(db_pr)

    workspace.status = "prs_generated"
    await db.commit()

    log.info(
        "policy_pull_requests.run",
        workspace_id=workspace_id,
        total_gaps=len(gaps_to_amend),
        pr_count=len(generated_prs),
    )

    return PolicyPullRequestRunRead(
        workspace_id=workspace_id,
        status="prs_generated",
        pr_count=len(generated_prs),
    )


@router.get(
    "/workspaces/{workspace_id}/policy-pull-requests",
    response_model=list[PolicyPullRequestRead],
)
async def list_policy_pull_requests(
    workspace_id: str,
    status: str | None = Query(None, description="Filter by status (pending/approved/etc)"),
    owner_id: str | None = Query(None, description="Filter by suggested owner ID"),
    risk_level: str | None = Query(None, description="Filter by risk level (high/medium/low)"),
    db: AsyncSession = Depends(get_db),
) -> list[PolicyPullRequest]:
    """List generated policy pull requests for a workspace with optional filters."""
    workspace = await db.get(Workspace, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail=f"Workspace '{workspace_id}' not found.")

    query = (
        select(PolicyPullRequest)
        .where(PolicyPullRequest.workspace_id == workspace_id)
        .options(
            selectinload(PolicyPullRequest.suggested_owner),
            selectinload(PolicyPullRequest.review_actions),
        )
        .order_by(PolicyPullRequest.created_at, PolicyPullRequest.id)
    )

    if status:
        query = query.where(PolicyPullRequest.status == status)
    if owner_id:
        query = query.where(PolicyPullRequest.suggested_owner_id == owner_id)
    if risk_level:
        query = query.where(PolicyPullRequest.risk_level == risk_level)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.post(
    "/policy-pull-requests/{pr_id}/review",
    response_model=PolicyPullRequestRead,
)
async def review_policy_pull_request(
    pr_id: str,
    review: ReviewActionCreate,
    db: AsyncSession = Depends(get_db),
) -> PolicyPullRequest:
    """Record a review action on a policy pull request and update its status."""
    pr_query = (
        select(PolicyPullRequest)
        .where(PolicyPullRequest.id == pr_id)
        .options(
            selectinload(PolicyPullRequest.suggested_owner),
            selectinload(PolicyPullRequest.review_actions),
        )
    )
    result = await db.execute(pr_query)
    pr = result.scalar_one_or_none()
    if not pr:
        raise HTTPException(status_code=404, detail=f"Policy pull request '{pr_id}' not found.")

    # Validate modification inputs
    if review.action == "modify" and not review.modified_text:
        raise HTTPException(
            status_code=400,
            detail="Modified text is required when action is 'modify'.",
        )

    # Map review action to PR status
    status_mapping = {
        "approve": "approved",
        "reject": "rejected",
        "modify": "modified",
        "escalate": "escalated",
    }
    pr.status = status_mapping[review.action]

    # Apply text modification if appropriate
    if review.action == "modify" and review.modified_text:
        pr.after_text = review.modified_text

    # Record review action
    action_record = ReviewAction(
        policy_pull_request_id=pr.id,
        action=review.action,
        reviewer_label=review.reviewer_label,
        comment=review.comment,
        modified_text=review.modified_text,
    )
    db.add(action_record)
    pr.review_actions.append(action_record)

    await db.commit()

    # Refresh PR to load new review action
    refresh_result = await db.execute(pr_query)
    updated_pr = refresh_result.scalar_one()

    log.info(
        "policy_pull_requests.review",
        pr_id=pr_id,
        action=review.action,
        new_status=updated_pr.status,
    )

    return updated_pr
