"""Thin typed client for the external LLM (Groq's OpenAI-compatible API).

The client shares the process-wide ``httpx.AsyncClient`` (no per-request churn)
and is disabled cleanly when no API key is configured, so callers can degrade
to LLM-free behavior instead of failing.
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import UTC
from typing import Any, Protocol

import httpx

from app.core.budget import SpendBudget


class LLMError(RuntimeError):
    """Raised when the LLM request or its JSON response is unusable."""


class LLMNotConfiguredError(LLMError):
    """Raised when an LLM call is attempted without a configured API key."""


class LLMBudgetExceeded(LLMError):
    """Raised when the daily LLM spend budget is exhausted."""


class LLMProvider(Protocol):
    """Interface implemented by ``LLMClient`` and test doubles."""

    @property
    def enabled(self) -> bool: ...

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> dict[str, Any]: ...


class LLMClient:
    """Groq chat-completions client with JSON mode and bounded retries."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_retries: int = 2,
        timeout: float | None = None,
        budget: SpendBudget | None = None,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._timeout = timeout
        self._budget = budget

    @property
    def enabled(self) -> bool:
        return bool(self._api_key)

    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        if not self.enabled:
            raise LLMNotConfiguredError("LLM API key is not configured")
        if self._budget is not None and not self._budget.consume():
            raise LLMBudgetExceeded("LLM daily limit reached")
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        data = await self._post_completions(payload, headers)
        content = _extract_content(data)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {content[:200]!r}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("LLM JSON response must be a top-level object")
        return parsed

    async def _post_completions(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                backoff = min(4.0, 0.5 * (2 ** (attempt - 1)))
                await asyncio.sleep(backoff * random.uniform(0.5, 1.0))
            try:
                response = await self._client.post(
                    url, json=payload, headers=headers, timeout=self._timeout
                )
            except httpx.TransportError as exc:
                last_error = exc
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_error = LLMError(f"upstream {response.status_code}")
                if response.status_code == 429:
                    retry_after = _retry_after_seconds(response)
                    if retry_after is not None and retry_after <= 15:
                        await asyncio.sleep(retry_after)
                await response.aread()
                continue
            if response.status_code != 200:
                raise LLMError(
                    f"LLM request failed ({response.status_code}): {response.text[:200]}"
                )
            data = response.json()
            if not isinstance(data, dict):
                raise LLMError("LLM response is not a JSON object")
            return data
        raise LLMError(f"LLM request failed after {self._max_retries + 1} attempts: {last_error}")


def _extract_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {data!r}") from exc
    if not isinstance(content, str):
        raise LLMError(f"LLM content is not a string: {content!r}")
    return content

def _retry_after_seconds(response: Any) -> float | None:
    """Seconds suggested by a 429 'Retry-After' header (delta-seconds or date).

    Returns ``None`` when the header is absent or unparsable so the caller can
    fall back to its normal backoff.
    """
    raw = response.headers.get("retry-after") if hasattr(response, "headers") else None
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:  # HTTP-date form
        from datetime import datetime
        from email.utils import parsedate_to_datetime

        moment = parsedate_to_datetime(raw)
        return max(0.0, (moment - datetime.now(UTC)).total_seconds())
    except (TypeError, ValueError):
        return None
