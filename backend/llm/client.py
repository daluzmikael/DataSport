"""Unified LLM client for OpenAI and Anthropic."""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load backend/.env when this module is imported (e.g. one-off python -c tests).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

Provider = Literal["openai", "anthropic"]


def openai_base_url() -> str:
    return (os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").strip()


class LLMNotConfiguredError(RuntimeError):
    pass


def _provider_env(name: str, default: str = "openai") -> Provider:
    raw = os.getenv(name, default).strip().lower()
    if raw not in ("openai", "anthropic"):
        raise ValueError(f"Invalid provider in {name}: {raw}")
    return raw  # type: ignore[return-value]


# Transient failures (rate limits, 5xx, dropped connections) are the common case and
# they used to surface as a 500 to the user. Retry a few times, then give up — if it
# fails this many times in a row the problem is not transient.
LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "3"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
LLM_RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))


def _is_retryable(exc: Exception) -> bool:
    """Retry connection problems, rate limits and 5xx; never retry a bad request.

    A malformed prompt or an unknown model fails identically every time, so retrying
    it just triples the latency before showing the same error.
    """
    name = type(exc).__name__
    if name in ("APIConnectionError", "APITimeoutError", "RateLimitError",
                "InternalServerError", "APIStatusError", "ServiceUnavailableError",
                "OverloadedError", "ConnectionError", "Timeout", "TimeoutError"):
        return True
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int):
        return status == 429 or status >= 500
    text = str(exc).lower()
    return any(s in text for s in ("timed out", "timeout", "connection", "rate limit",
                                   "overloaded", "temporarily unavailable"))


def _with_retries(call, label: str):
    """Run `call`, retrying transient failures with exponential backoff."""
    last: Exception | None = None
    for attempt in range(1, LLM_MAX_ATTEMPTS + 1):
        try:
            return call()
        except LLMNotConfiguredError:
            raise  # configuration, not transient
        except Exception as exc:  # noqa: BLE001 — classified by _is_retryable
            last = exc
            if attempt >= LLM_MAX_ATTEMPTS or not _is_retryable(exc):
                break
            delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
            logger.warning(
                "%s attempt %d/%d failed (%s: %s) — retrying in %.1fs",
                label, attempt, LLM_MAX_ATTEMPTS, type(exc).__name__, exc, delay,
            )
            time.sleep(delay)
    assert last is not None
    logger.error("%s failed after %d attempt(s): %s", label, LLM_MAX_ATTEMPTS, last)
    raise last


def chat_completion(
    *,
    provider: Provider,
    model: str,
    system: str,
    user: str,
    temperature: float = 0,
    max_tokens: int = 2000,
    extra_messages: list[dict[str, str]] | None = None,
) -> str:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if extra_messages:
        messages.extend(extra_messages)

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMNotConfiguredError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=openai_base_url(),
                        timeout=LLM_TIMEOUT_SECONDS)

        def _openai_call():
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
            )
            return (response.choices[0].message.content or "").strip()

        return _with_retries(_openai_call, f"openai/{model}")

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LLMNotConfiguredError("ANTHROPIC_API_KEY is not set")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise LLMNotConfiguredError("anthropic package not installed") from exc

    client = Anthropic(api_key=api_key, timeout=LLM_TIMEOUT_SECONDS)
    # Anthropic: system separate from messages
    anthropic_messages = [m for m in messages if m["role"] != "system"]
    system_text = system
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
            break

    def _anthropic_call():
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_text,
            messages=anthropic_messages,  # type: ignore[arg-type]
            temperature=temperature,
        )
        parts = [block.text for block in response.content if hasattr(block, "text")]
        return "".join(parts).strip()

    return _with_retries(_anthropic_call, f"anthropic/{model}")


def router_completion(system: str, user: str, extra_messages: list[dict[str, str]] | None = None) -> str:
    provider = _provider_env("ROUTER_PROVIDER", "openai")
    model = os.getenv("ROUTER_MODEL", "gpt-5.4-mini")
    return chat_completion(
        provider=provider,
        model=model,
        system=system,
        user=user,
        temperature=0,
        max_tokens=int(os.getenv("ROUTER_MAX_TOKENS", "1500")),
        extra_messages=extra_messages,
    )


def analyst_completion(system: str, user: str, extra_messages: list[dict[str, str]] | None = None) -> str:
    provider = _provider_env("ANALYST_PROVIDER", "openai")
    model = os.getenv("ANALYST_MODEL", "gpt-5.4-mini")
    return chat_completion(
        provider=provider,
        model=model,
        system=system,
        user=user,
        temperature=0,
        max_tokens=int(os.getenv("ANALYST_MAX_TOKENS", "2000")),
        extra_messages=extra_messages,
    )
