"""
Centralised AI client wrapper — supports OpenAI, Groq (free), and Gemini (free).
All AI calls go through this module so logging, retries, and model
selection are handled in one place.
"""
import json
import time
import logging
from typing import Any

from openai import AsyncOpenAI

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if settings.ai_provider == "groq":
            _client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        elif settings.ai_provider == "gemini":
            _client = AsyncOpenAI(
                api_key=settings.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
        else:
            # Support both OPENAI_API_KEY and OPENAI_KEY env var names
            api_key = settings.openai_api_key or settings.openai_key
            _client = AsyncOpenAI(api_key=api_key)
    return _client


def get_model() -> str:
    if settings.ai_provider == "groq":
        return settings.groq_model
    if settings.ai_provider == "gemini":
        return settings.gemini_model
    return settings.openai_model


async def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.4,
    max_tokens: int = 1500,
    response_format: str = "json_object",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Call the OpenAI chat completion API.

    Returns:
        (parsed_response_dict, log_record)

    The log_record is stored by callers so every prompt+response pair
    is persisted in the database.
    """
    client = get_client()
    start = time.perf_counter()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Gemini's OpenAI-compatible endpoint does not support response_format;
    # the system prompt already instructs it to reply with JSON.
    kwargs: dict = dict(
        model=get_model(),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if settings.ai_provider != "gemini":
        kwargs["response_format"] = (
            {"type": "json_object"} if response_format == "json_object" else {"type": "text"}
        )

    completion = await client.chat.completions.create(**kwargs)

    elapsed = round(time.perf_counter() - start, 3)
    raw = completion.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("AI returned non-JSON content: %s", raw)
        parsed = {"raw": raw}

    log_record = {
        "model": get_model(),
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw_response": raw,
        "latency_seconds": elapsed,
        "prompt_tokens": completion.usage.prompt_tokens if completion.usage else 0,
        "completion_tokens": completion.usage.completion_tokens if completion.usage else 0,
    }

    logger.info(
        "AI call completed in %.3fs | prompt_tokens=%d | completion_tokens=%d",
        elapsed,
        log_record["prompt_tokens"],
        log_record["completion_tokens"],
    )

    return parsed, log_record
