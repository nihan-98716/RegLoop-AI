"""Phase 7: Policy Pull Request Generator Service.

Generates policy pull requests/amendments for obligations with partial or missing coverage.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.workspace import (
    GapAnalysis,
    Obligation,
    PolicyMapping,
    PolicyPullRequest,
    ResponsibilityOwner,
)

POLICY_PR_PROMPT = """You are a senior compliance officer.

Given a regulatory obligation with a compliance gap, generate a policy amendment pull request to resolve the gap.

Generate a structured policy amendment including:
- title
- proposed_amendment
- before_text
- after_text

Return JSON only.
"""

MODEL_NAME = "local-pr-generator-v1"


class PolicyPrOutput(BaseModel):
    title: str = Field(min_length=5)
    proposed_amendment: str = Field(min_length=10)
    before_text: str
    after_text: str = Field(min_length=10)

    @field_validator("title", "proposed_amendment", "after_text")
    @classmethod
    def non_blank(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned


@dataclass(frozen=True)
class ValidatedPolicyPr:
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


def find_suggested_owner(
    obligation: Obligation,
    owners: list[ResponsibilityOwner],
) -> ResponsibilityOwner | None:
    """Finds the most relevant owner from the responsibility matrix.

    Matching rules:
      1. Exact match on compliance_domain vs owner.domain (case-insensitive).
      2. Substring match: owner.domain in obligation.compliance_domain (or vice-versa).
      3. Keyword match: owner.policy_area in obligation.statement (case-insensitive).
      4. Fallback to first owner.
    """
    if not owners:
        return None

    # Rule 1: Exact domain match
    if obligation.compliance_domain:
        obl_domain_lower = obligation.compliance_domain.strip().lower()
        for owner in owners:
            if owner.domain.strip().lower() == obl_domain_lower:
                return owner

    # Rule 2: Substring domain match
    if obligation.compliance_domain:
        obl_domain_lower = obligation.compliance_domain.strip().lower()
        for owner in owners:
            owner_dom_lower = owner.domain.strip().lower()
            if owner_dom_lower in obl_domain_lower or obl_domain_lower in owner_dom_lower:
                return owner

    # Rule 3: Policy area keyword in statement
    for owner in owners:
        policy_area_lower = owner.policy_area.strip().lower()
        if policy_area_lower and len(policy_area_lower) > 3:
            if policy_area_lower in obligation.statement.lower():
                return owner

    # Rule 4: Fallback to first owner
    return owners[0]


async def generate_pr_for_gap(
    obligation: Obligation,
    gap: GapAnalysis,
    mapping: PolicyMapping | None,
    owners: list[ResponsibilityOwner],
) -> ValidatedPolicyPr:
    """Policy pull request generator with OpenAI LLM support and deterministic fallback."""
    from app.config import settings
    from app.services.llm import call_openai_api

    # Lookup owner
    suggested_owner = find_suggested_owner(obligation, owners)
    owner_id = suggested_owner.id if suggested_owner else None

    # Before text from mapping excerpt
    before_text = ""
    if mapping and not mapping.is_no_match and mapping.policy_excerpt:
        before_text = mapping.policy_excerpt

    # If OpenAI API is enabled, call it
    if settings.openai_api_key and settings.llm_provider == "openai":
        user_prompt = (
            f"Regulatory Obligation:\n\"{obligation.statement}\"\n"
            f"Source reference: {obligation.source_reference}\n"
            f"Coverage status: {gap.coverage_status}\n"
            f"Reasoning for gap: {gap.reasoning}\n\n"
        )
        if before_text:
            user_prompt += f"Existing Policy Excerpt:\n\"{before_text}\"\n\n"
        else:
            user_prompt += "Existing Policy Excerpt: [None - Policy addition needed]\n\n"

        user_prompt += (
            "Generate a policy amendment. Return a JSON object with keys: "
            "'title', 'proposed_amendment', 'before_text', and 'after_text'. "
            "Ensure that 'before_text' matches the existing policy excerpt provided above."
        )

        raw_output = await call_openai_api(
            system_prompt=POLICY_PR_PROMPT,
            user_prompt=user_prompt,
            response_json=True,
            model="gpt-4o",
        )

        if raw_output:
            try:
                parsed = PolicyPrOutput.model_validate_json(raw_output)
                
                # Regulatory citation
                regulatory_citation = obligation.source_reference
                if obligation.source_excerpt:
                    regulatory_citation = f"{obligation.source_reference}: {obligation.source_excerpt}"

                return ValidatedPolicyPr(
                    obligation_id=obligation.id,
                    gap_analysis_id=gap.id,
                    title=parsed.title,
                    gap_description=gap.reasoning,
                    proposed_amendment=parsed.proposed_amendment,
                    regulatory_citation=regulatory_citation,
                    suggested_owner_id=owner_id,
                    risk_level=gap.risk_level,
                    confidence=gap.confidence,
                    before_text=parsed.before_text,
                    after_text=parsed.after_text,
                    status="pending",
                )
            except Exception as exc:
                import structlog
                structlog.get_logger().error("pull_request.openai_failed", error=str(exc))

    # Fallback to local rule-based mapping (deterministic generator)
    # Generate amendment & after text
    title = f"Policy Amendment: {obligation.compliance_domain or 'General Compliance'} Compliance"

    if gap.coverage_status == "partially_covered":
        proposed_amendment = (
            f"AMENDMENT: To fully satisfy the obligation under {obligation.source_reference}, "
            f"the firm shall enhance the policy to ensure: {obligation.statement}"
        )
        if before_text:
            after_text = f"{before_text}\n\n[Amendment]:\n{proposed_amendment}"
        else:
            after_text = proposed_amendment
    else:  # not_covered
        proposed_amendment = (
            f"POLICY ADDITION: The firm shall establish and maintain procedures to ensure that "
            f"{obligation.statement.rstrip('.')} in accordance with {obligation.source_reference}."
        )
        after_text = proposed_amendment

    # Validate schema
    try:
        output = PolicyPrOutput(
            title=title,
            proposed_amendment=proposed_amendment,
            before_text=before_text,
            after_text=after_text,
        )
    except ValidationError as exc:
        raise ValueError("Generated policy PR failed schema validation.") from exc

    # Regulatory citation
    regulatory_citation = obligation.source_reference
    if obligation.source_excerpt:
        regulatory_citation = f"{obligation.source_reference}: {obligation.source_excerpt}"

    return ValidatedPolicyPr(
        obligation_id=obligation.id,
        gap_analysis_id=gap.id,
        title=output.title,
        gap_description=gap.reasoning,
        proposed_amendment=output.proposed_amendment,
        regulatory_citation=regulatory_citation,
        suggested_owner_id=owner_id,
        risk_level=gap.risk_level,
        confidence=gap.confidence,
        before_text=output.before_text,
        after_text=output.after_text,
        status="pending",
    )
