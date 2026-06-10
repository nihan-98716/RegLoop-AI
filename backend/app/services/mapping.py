"""Phase 5: Policy mapping service.

Deterministic keyword + domain matching approach — no remote LLM call
required so the prototype is fully runnable offline and tests stay fast.

The public interface mirrors the obligations service so a real LLM provider
can be swapped in later without changing the router or persistence logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.workspace import DocumentChunk, Obligation


# ---------------------------------------------------------------------------
# Prompt template (documentation / future LLM use)
# ---------------------------------------------------------------------------

POLICY_MAPPING_PROMPT = """You are a regulatory compliance analyst.

Given ONE regulatory obligation and a set of candidate policy excerpts, decide
which policy section best addresses this obligation.

Return structured JSON:
{
  "document_chunk_id": "<id or null>",
  "policy_excerpt": "<verbatim excerpt or null>",
  "mapping_rationale": "<explanation>",
  "confidence": <0-100 integer>,
  "is_no_match": <true | false>
}

Rules:
- Set is_no_match to true when no excerpt adequately addresses the obligation.
- Prefer the most specific policy section.
- confidence reflects how well the policy addresses the obligation.
- Do not invent excerpts — use only text from the provided candidates.
"""

MODEL_NAME = "local-keyword-mapper-v1"


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class MappingOutput(BaseModel):
    document_chunk_id: str | None = None
    policy_excerpt: str | None = None
    mapping_rationale: str = Field(min_length=5)
    confidence: int = Field(ge=0, le=100)
    is_no_match: bool = False

    @field_validator("mapping_rationale")
    @classmethod
    def non_blank_rationale(cls, v: str) -> str:
        cleaned = " ".join(v.split())
        if not cleaned:
            raise ValueError("mapping_rationale cannot be blank")
        return cleaned


@dataclass(frozen=True)
class ValidatedMapping:
    obligation_id: str
    policy_document_id: str | None
    document_chunk_id: str | None
    policy_excerpt: str | None
    mapping_rationale: str
    confidence: int
    is_no_match: bool
    model_name: str


# ---------------------------------------------------------------------------
# Candidate retrieval — keyword + domain scoring
# ---------------------------------------------------------------------------

# Weights for term overlap scoring
_STRONG_OBLIGATION_VERBS = {
    "must", "shall", "required", "require", "mandate", "mandated",
}
_MEDIUM_VERBS = {
    "ensure", "maintain", "monitor", "report", "retain", "notify",
    "document", "review", "assess", "test", "approve",
}

# Minimum overlap score to be considered a match
_MATCH_THRESHOLD = 30


def _tokenize(text: str) -> set[str]:
    """Lower-case word-level tokenization, strip punctuation."""
    import re
    return set(re.findall(r"[a-z]+", text.lower()))


def _score_chunk(obligation: Obligation, chunk: DocumentChunk) -> int:
    """Return a 0-100 relevance score between an obligation and a chunk."""
    obl_tokens = _tokenize(obligation.statement)
    chunk_tokens = _tokenize(chunk.text)

    # Core term overlap
    common = obl_tokens & chunk_tokens
    if not common:
        return 0

    # Strong verb presence in both
    strong_in_common = common & _STRONG_OBLIGATION_VERBS
    medium_in_common = common & _MEDIUM_VERBS

    base = min(40, len(common) * 4)
    strong_bonus = len(strong_in_common) * 10
    medium_bonus = len(medium_in_common) * 5

    # Domain bonus: if obligation has a compliance_domain and chunk section
    # label contains that domain keyword
    domain_bonus = 0
    if obligation.compliance_domain and chunk.section_label:
        domain_kw = obligation.compliance_domain.lower()
        if domain_kw in chunk.section_label.lower():
            domain_bonus = 15

    return min(95, base + strong_bonus + medium_bonus + domain_bonus)


def retrieve_candidate_chunks(
    obligation: Obligation,
    policy_chunks: list[DocumentChunk],
    top_k: int = 5,
) -> list[tuple[DocumentChunk, int]]:
    """Return up to top_k policy chunks sorted by relevance score (desc)."""
    scored = [
        (chunk, _score_chunk(obligation, chunk))
        for chunk in policy_chunks
        if chunk.text.strip()
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ---------------------------------------------------------------------------
# Main mapping function
# ---------------------------------------------------------------------------

async def map_obligation_to_policy(
    obligation: Obligation,
    policy_chunks: list[DocumentChunk],
    chunk_to_doc_id: dict[str, str],
) -> ValidatedMapping:
    """Produce a ValidatedMapping for one obligation.

    Args:
        obligation: The obligation to map.
        policy_chunks: All policy document chunks in the workspace.
        chunk_to_doc_id: Maps chunk.id -> document.id for policy documents.
    """
    from app.config import settings
    from app.services.llm import call_openai_api

    if settings.openai_api_key and settings.llm_provider == "openai":
        candidates = retrieve_candidate_chunks(obligation, policy_chunks, top_k=5)
        if candidates:
            user_prompt = f"Regulatory Obligation statement to map:\n\"{obligation.statement}\"\n\nCandidate Policy Sections:\n"
            for index, (chunk, score) in enumerate(candidates):
                user_prompt += f"--- Candidate ID: {chunk.id} ---\n{chunk.text}\n\n"

            user_prompt += "Evaluate each candidate chunk and decide which is the best match. Remember: if no section is a good match, set is_no_match to true, document_chunk_id to null, and policy_excerpt to null."

            raw_output = await call_openai_api(
                system_prompt=POLICY_MAPPING_PROMPT,
                user_prompt=user_prompt,
                response_json=True,
                model="gpt-4o",
            )
            if raw_output:
                try:
                    parsed = MappingOutput.model_validate_json(raw_output)

                    matched_chunk = None
                    if not parsed.is_no_match and parsed.document_chunk_id:
                        for c, _ in candidates:
                            if c.id == parsed.document_chunk_id:
                                matched_chunk = c
                                break

                    if matched_chunk:
                        return ValidatedMapping(
                            obligation_id=obligation.id,
                            policy_document_id=chunk_to_doc_id.get(matched_chunk.id),
                            document_chunk_id=matched_chunk.id,
                            policy_excerpt=parsed.policy_excerpt or matched_chunk.text[:500],
                            mapping_rationale=parsed.mapping_rationale,
                            confidence=parsed.confidence,
                            is_no_match=False,
                            model_name="gpt-4o",
                        )
                    else:
                        return ValidatedMapping(
                            obligation_id=obligation.id,
                            policy_document_id=None,
                            document_chunk_id=None,
                            policy_excerpt=None,
                            mapping_rationale=parsed.mapping_rationale,
                            confidence=parsed.confidence,
                            is_no_match=True,
                            model_name="gpt-4o",
                        )
                except Exception as exc:
                    import structlog
                    structlog.get_logger().error("mapping.openai_failed", error=str(exc))

    # Fallback to local rule-based mapping
    candidates = retrieve_candidate_chunks(obligation, policy_chunks)

    if not candidates or candidates[0][1] < _MATCH_THRESHOLD:
        # No good match found
        raw = MappingOutput(
            document_chunk_id=None,
            policy_excerpt=None,
            mapping_rationale=(
                "No policy section found that adequately addresses this obligation. "
                "This represents a coverage gap requiring a new or updated policy."
            ),
            confidence=10,
            is_no_match=True,
        )
        return ValidatedMapping(
            obligation_id=obligation.id,
            policy_document_id=None,
            document_chunk_id=None,
            policy_excerpt=None,
            mapping_rationale=raw.mapping_rationale,
            confidence=raw.confidence,
            is_no_match=True,
            model_name=MODEL_NAME,
        )

    best_chunk, best_score = candidates[0]

    # Extract a representative excerpt (first 500 chars)
    excerpt = " ".join(best_chunk.text.split())[:500]
    if len(" ".join(best_chunk.text.split())) > 500:
        excerpt = excerpt.rstrip() + "..."

    # Build rationale
    common_tokens = _tokenize(obligation.statement) & _tokenize(best_chunk.text)
    shared_terms = sorted(common_tokens - _STRONG_OBLIGATION_VERBS - {"the", "a", "an", "to", "of", "in", "and", "or", "with"})[:5]
    rationale_parts = [
        f"Policy section addresses the obligation via shared terms: {', '.join(shared_terms)}." if shared_terms else "Policy section shares relevant regulatory language with the obligation."
    ]
    if best_chunk.section_label:
        rationale_parts.append(f"Section: '{best_chunk.section_label}'.")
    if best_chunk.page_number:
        rationale_parts.append(f"Page {best_chunk.page_number}.")

    rationale = " ".join(rationale_parts)

    try:
        raw = MappingOutput(
            document_chunk_id=best_chunk.id,
            policy_excerpt=excerpt,
            mapping_rationale=rationale,
            confidence=best_score,
            is_no_match=False,
        )
    except ValidationError as exc:
        raise ValueError("Policy mapping output failed schema validation.") from exc

    return ValidatedMapping(
        obligation_id=obligation.id,
        policy_document_id=chunk_to_doc_id.get(best_chunk.id),
        document_chunk_id=raw.document_chunk_id,
        policy_excerpt=raw.policy_excerpt,
        mapping_rationale=raw.mapping_rationale,
        confidence=raw.confidence,
        is_no_match=raw.is_no_match,
        model_name=MODEL_NAME,
    )


async def map_all_obligations(
    obligations: list[Obligation],
    policy_chunks: list[DocumentChunk],
    chunk_to_doc_id: dict[str, str],
) -> list[ValidatedMapping]:
    """Map every obligation, returning one ValidatedMapping per obligation."""
    return [
        await map_obligation_to_policy(obl, policy_chunks, chunk_to_doc_id)
        for obl in obligations
    ]
