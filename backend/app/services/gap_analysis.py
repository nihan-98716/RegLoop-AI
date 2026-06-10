"""Phase 6: Gap analysis service.

Deterministic coverage assessment based on mapping confidence and match status.
The public interface is structured so a real LLM provider can replace this
logic without changing the router or persistence layer.

Coverage rules (deterministic fallback — P1):
  - is_no_match=True                         → not_covered   → high risk
  - is_no_match=False AND confidence >= 70   → fully_covered → low risk
  - is_no_match=False AND confidence >= 40   → partially_covered → medium risk
  - is_no_match=False AND confidence < 40    → not_covered   → high risk

Strong-verb bonus:
  If the obligation contains mandatory language ("must", "shall", "required")
  and coverage is partial, risk is escalated to high.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.workspace import Obligation, PolicyMapping


# ---------------------------------------------------------------------------
# Prompt template (documentation / future LLM use)
# ---------------------------------------------------------------------------

GAP_ANALYSIS_PROMPT = """You are a senior regulatory compliance analyst.

Given a regulatory obligation and the best matching policy excerpt (or a
no-match result), assess whether the internal policy adequately satisfies
the obligation.

Return structured JSON:
{
  "coverage_status": "fully_covered" | "partially_covered" | "not_covered",
  "risk_level": "high" | "medium" | "low",
  "reasoning": "<concise explanation of the assessment>",
  "source_citations": "<relevant policy or regulation references, or null>",
  "confidence": <0-100 integer>
}

Rules:
- fully_covered: policy explicitly and completely addresses the obligation.
- partially_covered: policy addresses some aspects but has gaps.
- not_covered: no relevant policy text exists for this obligation.
- risk escalates when obligations use mandatory language (must, shall, required).
- Always cite evidence for your decision in reasoning.
"""

MODEL_NAME = "local-gap-analyzer-v1"

CoverageStatus = Literal["fully_covered", "partially_covered", "not_covered"]
RiskLevel = Literal["high", "medium", "low"]

_MANDATORY_VERBS = {"must", "shall", "required", "require", "mandated"}


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class GapAnalysisOutput(BaseModel):
    coverage_status: CoverageStatus
    risk_level: RiskLevel
    reasoning: str = Field(min_length=10)
    source_citations: str | None = None
    confidence: int = Field(ge=0, le=100)

    @field_validator("reasoning")
    @classmethod
    def non_blank_reasoning(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("reasoning cannot be blank")
        return cleaned

    @field_validator("source_citations")
    @classmethod
    def clean_citations(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = " ".join(v.split())
        return cleaned or None


# ---------------------------------------------------------------------------
# Validated output dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ValidatedGapAnalysis:
    obligation_id: str
    policy_mapping_id: str | None
    coverage_status: str
    risk_level: str
    reasoning: str
    source_citations: str | None
    confidence: int
    model_name: str


# ---------------------------------------------------------------------------
# Deterministic assessment rules (P1 fallback)
# ---------------------------------------------------------------------------

def _has_mandatory_language(statement: str) -> bool:
    import re
    tokens = set(re.findall(r"[a-z]+", statement.lower()))
    return bool(tokens & _MANDATORY_VERBS)


def _assess_coverage(
    mapping: PolicyMapping,
) -> tuple[CoverageStatus, RiskLevel, int]:
    """Apply deterministic rules to derive coverage status, risk, and confidence.

    Returns (coverage_status, risk_level, confidence).
    """
    if mapping.is_no_match:
        return "not_covered", "high", 15

    conf = mapping.confidence

    if conf >= 70:
        return "fully_covered", "low", min(95, conf)

    if conf >= 40:
        return "partially_covered", "medium", conf

    # Low confidence match — treat as not_covered
    return "not_covered", "high", max(15, conf - 10)


def _escalate_risk_if_mandatory(
    statement: str,
    coverage: CoverageStatus,
    risk: RiskLevel,
) -> RiskLevel:
    """Escalate risk to high for partial coverage of mandatory obligations."""
    if coverage == "partially_covered" and _has_mandatory_language(statement):
        return "high"
    return risk


def _build_reasoning(
    obligation: Obligation,
    mapping: PolicyMapping,
    coverage: CoverageStatus,
    risk: RiskLevel,
) -> str:
    """Compose a structured reasoning string from available evidence."""
    parts: list[str] = []

    if mapping.is_no_match:
        parts.append(
            "No policy section was found that addresses this obligation. "
            "This indicates a coverage gap in the current policy framework."
        )
    elif coverage == "fully_covered":
        parts.append(
            f"The policy section adequately addresses this obligation "
            f"(mapping confidence: {mapping.confidence}%)."
        )
        if mapping.mapping_rationale:
            parts.append(mapping.mapping_rationale)
    elif coverage == "partially_covered":
        parts.append(
            f"A related policy section was found (confidence: {mapping.confidence}%) "
            f"but does not fully satisfy all aspects of the obligation."
        )
        if mapping.mapping_rationale:
            parts.append(mapping.mapping_rationale)
        if _has_mandatory_language(obligation.statement):
            parts.append(
                "The obligation uses mandatory language (must/shall/required), "
                "which elevates risk for partial coverage."
            )
    else:  # not_covered with a low-confidence match
        parts.append(
            f"The best matching policy section has low confidence ({mapping.confidence}%), "
            f"insufficient to demonstrate regulatory compliance."
        )

    risk_label = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}[risk]
    parts.append(f"Risk level: {risk_label}.")

    return " ".join(parts)


def _build_citations(
    obligation: Obligation,
    mapping: PolicyMapping,
) -> str | None:
    """Compose a source citations string."""
    parts = []
    if obligation.source_reference:
        parts.append(f"Regulation: {obligation.source_reference}")
    if not mapping.is_no_match and mapping.policy_excerpt:
        excerpt_preview = mapping.policy_excerpt[:120].rstrip()
        if len(mapping.policy_excerpt) > 120:
            excerpt_preview += "..."
        parts.append(f'Policy excerpt: "{excerpt_preview}"')
    return "; ".join(parts) if parts else None


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def analyse_gap(
    obligation: Obligation,
    mapping: PolicyMapping,
) -> ValidatedGapAnalysis:
    """Produce a ValidatedGapAnalysis for one obligation/mapping pair."""
    coverage, risk, conf = _assess_coverage(mapping)
    risk = _escalate_risk_if_mandatory(obligation.statement, coverage, risk)
    reasoning = _build_reasoning(obligation, mapping, coverage, risk)
    citations = _build_citations(obligation, mapping)

    try:
        output = GapAnalysisOutput(
            coverage_status=coverage,
            risk_level=risk,
            reasoning=reasoning,
            source_citations=citations,
            confidence=conf,
        )
    except ValidationError as exc:
        raise ValueError("Gap analysis output failed schema validation.") from exc

    return ValidatedGapAnalysis(
        obligation_id=obligation.id,
        policy_mapping_id=mapping.id,
        coverage_status=output.coverage_status,
        risk_level=output.risk_level,
        reasoning=output.reasoning,
        source_citations=output.source_citations,
        confidence=output.confidence,
        model_name=MODEL_NAME,
    )


def analyse_all_gaps(
    obligation_mapping_pairs: list[tuple[Obligation, PolicyMapping]],
) -> list[ValidatedGapAnalysis]:
    """Run gap analysis for all obligation/mapping pairs."""
    return [analyse_gap(obl, mapping) for obl, mapping in obligation_mapping_pairs]
