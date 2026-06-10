"""Phase 4 obligation extraction and structured output validation."""

import json
import re
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.workspace import DocumentChunk


OBLIGATION_EXTRACTION_PROMPT = """Extract concrete regulatory obligations from the provided regulatory text.
Return only structured JSON. Do not summarize the document.
Each obligation must include statement, source_reference, source_excerpt, confidence,
and optional compliance_domain. Confidence is an integer from 0 to 100.
"""

OBLIGATION_KEYWORDS = (
    "must",
    "shall",
    "required",
    "require",
    "ensure",
    "maintain",
    "report",
    "retain",
    "notify",
    "monitor",
    "document",
)


class ExtractedObligation(BaseModel):
    statement: str = Field(min_length=10)
    source_reference: str = Field(min_length=1)
    source_excerpt: str = Field(min_length=10)
    confidence: int = Field(ge=0, le=100)
    compliance_domain: str | None = None

    @field_validator("statement", "source_reference", "source_excerpt")
    @classmethod
    def non_blank(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("value cannot be blank")
        return cleaned

    @field_validator("compliance_domain")
    @classmethod
    def clean_domain(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None


class ObligationExtractionResult(BaseModel):
    obligations: list[ExtractedObligation]


@dataclass(frozen=True)
class ValidatedObligation:
    statement: str
    source_reference: str
    source_excerpt: str
    confidence: int
    compliance_domain: str | None


async def extract_obligations_from_chunks(
    chunks: list[DocumentChunk],
    model_name: str = "gpt-4o",
) -> tuple[list[ValidatedObligation], str]:
    """Extract obligations from regulatory chunks and validate the result schema.

    If OpenAI API key is set, makes a remote call. Otherwise, falls back to the local deterministic extractor.
    """
    from app.config import settings
    from app.services.llm import call_openai_api

    if settings.openai_api_key and settings.llm_provider == "openai":
        # Prepare chunks text
        user_prompt = "Please extract regulatory obligations from the following document chunks:\n\n"
        for index, chunk in enumerate(chunks):
            ref = []
            if chunk.page_number is not None:
                ref.append(f"page {chunk.page_number}")
            if chunk.section_label:
                ref.append(chunk.section_label)
            ref_str = ", ".join(ref) or f"chunk {index + 1}"
            user_prompt += f"--- Chunk Ref: {ref_str} ---\n{chunk.text}\n\n"

        user_prompt += "Ensure each obligation statement is clear, captures the specific duty, and uses the exact reference string provided (e.g. 'page 1') for the 'source_reference' field."

        raw_output = await call_openai_api(
            system_prompt=OBLIGATION_EXTRACTION_PROMPT,
            user_prompt=user_prompt,
            response_json=True,
            model=model_name,
        )
        if raw_output:
            try:
                parsed = parse_obligation_provider_output(raw_output)
                validated = [
                    ValidatedObligation(
                        statement=item.statement,
                        source_reference=item.source_reference,
                        source_excerpt=item.source_excerpt,
                        confidence=item.confidence,
                        compliance_domain=item.compliance_domain,
                    )
                    for item in parsed.obligations
                ]
                return validated, model_name
            except Exception as exc:
                import structlog
                structlog.get_logger().error("obligations.extraction_openai_failed", error=str(exc))

    # Fallback to local rule-based extractor
    fallback_model = "local-rule-extractor-v1"
    candidates = []
    seen: set[str] = set()
    for chunk in chunks:
        for sentence in _candidate_sentences(chunk.text):
            if not _looks_like_obligation(sentence):
                continue
            normalized = " ".join(sentence.split())
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            candidates.append(
                {
                    "statement": _to_obligation_statement(normalized),
                    "source_reference": _source_reference(chunk),
                    "source_excerpt": normalized[:700],
                    "confidence": _confidence(normalized),
                    "compliance_domain": _domain(normalized),
                }
            )

    try:
        parsed = ObligationExtractionResult.model_validate({"obligations": candidates})
    except ValidationError as exc:
        raise ValueError("Obligation extraction output failed schema validation.") from exc

    validated = [
        ValidatedObligation(
            statement=item.statement,
            source_reference=item.source_reference,
            source_excerpt=item.source_excerpt,
            confidence=item.confidence,
            compliance_domain=item.compliance_domain,
        )
        for item in parsed.obligations
    ]
    return validated, fallback_model


def validate_obligation_payload(payload: dict) -> ObligationExtractionResult:
    """Validate a provider payload. Exposed for focused schema tests."""
    return ObligationExtractionResult.model_validate(payload)


def parse_obligation_provider_output(raw_output: str) -> ObligationExtractionResult:
    """Parse provider JSON with small repairs for common LLM formatting drift."""
    candidate = raw_output.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate, flags=re.I)
        candidate = re.sub(r"\s*```$", "", candidate)

    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(candidate[start : end + 1])

    if isinstance(payload, list):
        payload = {"obligations": payload}
    return validate_obligation_payload(payload)


def _candidate_sentences(text: str) -> list[str]:
    compact = " ".join(text.split())
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]


def _looks_like_obligation(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(keyword in lowered for keyword in OBLIGATION_KEYWORDS)


def _to_obligation_statement(sentence: str) -> str:
    return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."


def _source_reference(chunk: DocumentChunk) -> str:
    parts = []
    if chunk.page_number is not None:
        parts.append(f"page {chunk.page_number}")
    if chunk.section_label:
        parts.append(chunk.section_label)
    if not parts:
        parts.append(f"chunk {chunk.chunk_index + 1}")
    return ", ".join(parts)


def _confidence(sentence: str) -> int:
    lowered = sentence.lower()
    strong = sum(1 for word in ("must", "shall", "required") if word in lowered)
    medium = sum(1 for word in ("ensure", "maintain", "report", "retain", "notify") if word in lowered)
    return min(95, 72 + strong * 8 + medium * 4)


def _domain(sentence: str) -> str | None:
    lowered = sentence.lower()
    if any(word in lowered for word in ("report", "notify", "notification")):
        return "Reporting"
    if any(word in lowered for word in ("retain", "record", "audit", "evidence")):
        return "Records"
    if any(word in lowered for word in ("monitor", "review", "test")):
        return "Monitoring"
    if any(word in lowered for word in ("approve", "governance", "board")):
        return "Governance"
    return None
