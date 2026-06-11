"""Unit tests for multi-provider LLM fallback and prompt engineering effectiveness."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.config import settings
from app.services.llm import (
    call_anthropic_api,
    call_gemini_api,
    call_llm_api,
    call_openai_api,
)
from app.services.mapping import POLICY_MAPPING_PROMPT
from app.services.obligations import OBLIGATION_EXTRACTION_PROMPT


@pytest.mark.anyio
async def test_prompt_engineering_effectiveness() -> None:
    """Verify that our prompts explicitly enforce structured JSON formatting and key fields."""
    # Obligation extraction prompt checks
    assert "json" in OBLIGATION_EXTRACTION_PROMPT.lower()
    assert "statement" in OBLIGATION_EXTRACTION_PROMPT
    assert "source_reference" in OBLIGATION_EXTRACTION_PROMPT
    assert "confidence" in OBLIGATION_EXTRACTION_PROMPT
    assert "compliance_domain" in OBLIGATION_EXTRACTION_PROMPT

    # Policy mapping prompt checks
    assert "json" in POLICY_MAPPING_PROMPT.lower()
    assert "document_chunk_id" in POLICY_MAPPING_PROMPT
    assert "policy_excerpt" in POLICY_MAPPING_PROMPT
    assert "confidence" in POLICY_MAPPING_PROMPT
    assert "is_no_match" in POLICY_MAPPING_PROMPT


@pytest.mark.anyio
async def test_llm_fallback_routing_openai_to_anthropic() -> None:
    """Test that unified call_llm_api routes and falls back if OpenAI fails but Anthropic is configured."""
    original_provider = settings.llm_provider
    original_openai = settings.openai_api_key
    original_anthropic = settings.anthropic_api_key
    original_google = settings.google_api_key

    settings.llm_provider = "openai"
    settings.openai_api_key = "fake-openai-key"
    settings.anthropic_api_key = "fake-anthropic-key"
    settings.google_api_key = ""

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # First response (OpenAI) fails with 429
            mock_resp_openai = AsyncMock()
            mock_resp_openai.status_code = 429
            mock_resp_openai.text = "Too Many Requests"

            # Second response (Anthropic) succeeds with 200
            mock_resp_anthropic = AsyncMock()
            mock_resp_anthropic.status_code = 200
            from unittest.mock import MagicMock
            mock_resp_anthropic.json = MagicMock(return_value={
                "content": [{"text": '{"result": "success-anthropic"}'}]
            })

            mock_client.post.side_effect = [mock_resp_openai, mock_resp_anthropic]

            res = await call_llm_api("sys", "user", response_json=True)
            assert res == '{"result": "success-anthropic"}'
            
            # Assert both endpoints were called in fallback order
            assert mock_client.post.call_count == 2
    finally:
        settings.llm_provider = original_provider
        settings.openai_api_key = original_openai
        settings.anthropic_api_key = original_anthropic
        settings.google_api_key = original_google


@pytest.mark.anyio
async def test_llm_fallback_routing_all_fail() -> None:
    """Test that call_llm_api returns None if all providers fail."""
    original_provider = settings.llm_provider
    original_openai = settings.openai_api_key
    original_anthropic = settings.anthropic_api_key
    original_google = settings.google_api_key

    settings.llm_provider = "openai"
    settings.openai_api_key = "fake-openai-key"
    settings.anthropic_api_key = ""
    settings.google_api_key = ""

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            mock_resp = AsyncMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_client.post.return_value = mock_resp

            res = await call_llm_api("sys", "user", response_json=True)
            assert res is None
    finally:
        settings.llm_provider = original_provider
        settings.openai_api_key = original_openai
        settings.anthropic_api_key = original_anthropic
        settings.google_api_key = original_google


@pytest.mark.anyio
async def test_llm_billing_error_bails_out_immediately() -> None:
    """Test that billing/quota errors short-circuit the retry loop instead of cascading."""
    original_openai = settings.openai_api_key
    original_anthropic = settings.anthropic_api_key
    settings.openai_api_key = "fake-openai-key"
    settings.anthropic_api_key = ""

    try:
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            from unittest.mock import MagicMock
            mock_resp = AsyncMock()
            mock_resp.status_code = 429
            mock_resp.text = "insufficient_quota"
            mock_resp.json = MagicMock(return_value={
                "error": {"code": "insufficient_quota", "message": "You exceeded your quota."}
            })
            mock_client.post.return_value = mock_resp

            res = await call_llm_api("sys", "user", response_json=True)
            # Should return None and not call post more than once
            assert res is None
            assert mock_client.post.call_count == 1  # bail-out after first billing error
    finally:
        settings.openai_api_key = original_openai
        settings.anthropic_api_key = original_anthropic


@pytest.mark.anyio
async def test_gap_analysis_prompt_enforces_required_fields() -> None:
    """Verify the gap analysis prompt explicitly requires all output schema fields."""
    from app.services.gap_analysis import GAP_ANALYSIS_PROMPT

    # All output schema fields must be named in the prompt
    for field in ("coverage_status", "risk_level", "reasoning", "source_citations", "confidence"):
        assert field in GAP_ANALYSIS_PROMPT, f"Prompt missing required field: {field}"

    # Prompt must enumerate the valid enumeration values
    for value in ("fully_covered", "partially_covered", "not_covered"):
        assert value in GAP_ANALYSIS_PROMPT, f"Prompt missing coverage value: {value}"
    for level in ("high", "medium", "low"):
        assert level in GAP_ANALYSIS_PROMPT, f"Prompt missing risk level: {level}"


@pytest.mark.anyio
async def test_pull_request_prompt_enforces_required_fields() -> None:
    """Verify the PR generation prompt explicitly requires all output schema fields."""
    from app.services.pull_request import POLICY_PR_PROMPT

    for field in ("title", "proposed_amendment", "before_text", "after_text"):
        assert field in POLICY_PR_PROMPT, f"PR prompt missing required field: {field}"
    assert "json" in POLICY_PR_PROMPT.lower(), "PR prompt must enforce JSON output"
