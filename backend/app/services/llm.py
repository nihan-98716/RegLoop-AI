"""OpenAI API integration service using httpx."""

import httpx
from app.config import settings
from app.logging_config import get_logger

log = get_logger(__name__)


async def call_openai_api(
    system_prompt: str,
    user_prompt: str,
    response_json: bool = True,
    model: str = "gpt-4o",
) -> str | None:
    """Make an async API call to OpenAI's Chat Completions endpoint."""
    if not settings.openai_api_key or settings.llm_provider != "openai":
        log.debug("llm.openai_disabled", reason="API key is missing or LLM_PROVIDER is not 'openai'")
        return None

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key.strip()}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }

    if response_json:
        payload["response_format"] = {"type": "json_object"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            if response.status_code != 200:
                log.error(
                    "llm.openai_error",
                    status_code=response.status_code,
                    response_text=response.text,
                )
                return None

            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as exc:
        log.error("llm.openai_exception", error=str(exc))
        return None
