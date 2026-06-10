"""Pydantic schemas for policy pull requests."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ingestion import ResponsibilityOwnerRead

PrStatus = Literal["pending", "approved", "rejected", "modified", "escalated"]
ReviewActionType = Literal["approve", "reject", "modify", "escalate"]


class ReviewActionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_pull_request_id: str
    action: str
    reviewer_label: str
    comment: str | None
    modified_text: str | None
    created_at: datetime


class ReviewActionCreate(BaseModel):
    action: ReviewActionType
    reviewer_label: str = Field(min_length=1)
    comment: str | None = None
    modified_text: str | None = None


class PolicyPullRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    obligation_id: str
    gap_analysis_id: str
    title: str
    gap_description: str
    proposed_amendment: str
    regulatory_citation: str | None
    suggested_owner_id: str | None
    risk_level: str
    confidence: int
    before_text: str
    after_text: str
    status: str
    created_at: datetime
    updated_at: datetime

    suggested_owner: ResponsibilityOwnerRead | None = None
    review_actions: list[ReviewActionRead] = []


class PolicyPullRequestRunRead(BaseModel):
    workspace_id: str
    status: str
    pr_count: int
