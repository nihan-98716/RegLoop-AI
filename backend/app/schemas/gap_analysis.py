"""Pydantic schemas for gap analysis."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


CoverageStatus = Literal["fully_covered", "partially_covered", "not_covered"]
RiskLevel = Literal["high", "medium", "low"]


class GapAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    obligation_id: str
    policy_mapping_id: str | None
    coverage_status: str
    risk_level: str
    reasoning: str
    source_citations: str | None
    confidence: int
    model_name: str
    created_at: datetime


class GapAnalysisRunRead(BaseModel):
    workspace_id: str
    status: str
    obligation_count: int
    fully_covered: int
    partially_covered: int
    not_covered: int
    high_risk: int
    model_name: str
