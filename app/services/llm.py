"""Thin typed client for the external LLM (Groq's OpenAI-compatible API).

The client shares the process-wide ``httpx.AsyncClient`` (no per-request churn)
and is disabled cleanly when no API key is configured, so callers can degrade
to LLM-free behavior instead of failing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import UTC
from typing import Any, Protocol

import httpx

from app.core.budget import SpendBudget

logger = logging.getLogger(__name__)

# Groq's structured error code for "the model did not emit usable JSON".
# Callers must not substring-match this themselves — it lives here so the
# classification stays in one place.
LLM_JSON_FAILURE_MARKER = "json_validate_failed"


class LLMError(RuntimeError):
    """Raised when the LLM request or its JSON response is unusable."""


class LLMNotConfiguredError(LLMError):
    """Raised when an LLM call is attempted without a configured API key."""


class LLMBudgetExceeded(LLMError):
    """Raised when the daily LLM spend budget is exhausted."""


class LLMJsonValidationError(LLMError):
    """Raised when the model produced something that is not usable JSON.

    Covers both the upstream structured failure (Groq's 400 with
    ``error.code == "json_validate_failed"``) and this client's own
    decode/shape checks, so callers classify by type instead of by
    substring-matching a free-text message.
    """


def _truncate(text: str, limit: int = 200) -> str:
    """Bound upstream/model text embedded in exception messages and logs."""
    return text if len(text) <= limit else text[:limit]


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
            raise LLMJsonValidationError(
                f"LLM returned invalid JSON: {_truncate(content)!r}"
            ) from exc
        if not isinstance(parsed, dict):
            raise LLMJsonValidationError(
                f"LLM JSON response must be a top-level object, got "
                f"{type(parsed).__name__}: {_truncate(content)!r}"
            )
        return parsed

    async def _post_completions(
        self, payload: dict[str, Any], headers: dict[str, str]
    ) -> dict[str, Any]:
        url = f"{self._base_url}/chat/completions"
        last_error: Exception | None = None
        honored_retry_after = False
        for attempt in range(self._max_retries + 1):
            # A 429 whose Retry-After we already waited out must not also pay
            # the jittered backoff at the top of this iteration — that double
            # sleep was real latency, not a documentation gap.
            sleep_path = "none"
            if attempt > 0 and not honored_retry_after:
                backoff = min(4.0, 0.5 * (2 ** (attempt - 1)))
                await asyncio.sleep(backoff * random.uniform(0.5, 1.0))
                sleep_path = "backoff"
            honored_retry_after = False
            if attempt > 0:
                logger.warning(
                    "llm retry attempt=%d/%d sleep=%s",
                    attempt + 1,
                    self._max_retries + 1,
                    sleep_path,
                )
            try:
                response = await self._client.post(
                    url, json=payload, headers=headers, timeout=self._timeout
                )
            except httpx.TransportError as exc:
                last_error = exc
                logger.warning(
                    "llm transport error attempt=%d/%d error=%s",
                    attempt + 1,
                    self._max_retries + 1,
                    type(exc).__name__,
                )
                continue
            if response.status_code == 429 or response.status_code >= 500:
                last_error = LLMError(f"upstream {response.status_code}")
                if response.status_code == 429:
                    retry_after = _retry_after_seconds(response)
                    if retry_after is not None and retry_after <= 15:
                        await asyncio.sleep(retry_after)
                        honored_retry_after = True
                        sleep_path = "retry-after"
                logger.warning(
                    "llm upstream error attempt=%d/%d status=%d sleep=%s",
                    attempt + 1,
                    self._max_retries + 1,
                    response.status_code,
                    sleep_path,
                )
                await response.aread()
                continue
            if response.status_code != 200:
                raise _non_200_error(response)
            data = response.json()
            if not isinstance(data, dict):
                raise LLMError("LLM response is not a JSON object")
            return data
        logger.error(
            "llm retries exhausted attempts=%d last_error=%s",
            self._max_retries + 1,
            _truncate(str(last_error)),
        )
        raise LLMError(f"LLM request failed after {self._max_retries + 1} attempts: {last_error}")


def _non_200_error(response: httpx.Response) -> LLMError:
    """Classify a non-200 response as a typed LLM error.

    ``LLM_JSON_FAILURE_MARKER`` is checked structurally first: Groq reports a
    model-generated-JSON failure as a 400 whose body carries
    ``error.code == "json_validate_failed"``. ``LLM_BASE_URL`` is
    configurable, so a provider that doesn't emit that shape falls back to
    the historical substring heuristic — flagged in the message wording so the
    fallback (which decides whether a failure is retried and billed again) is
    never mistaken for the structural match.
    """
    text = response.text
    if response.status_code == 400:
        try:
            data = response.json()
        except (json.JSONDecodeError, ValueError):
            data = None
        if isinstance(data, dict):
            error = data.get("error")
            code = error.get("code") if isinstance(error, dict) else None
            if code == "json_validate_failed":
                return LLMJsonValidationError(
                    f"LLM request failed (400, {LLM_JSON_FAILURE_MARKER}): {_truncate(text)}"
                )
        if "Failed to generate JSON" in text:
            logger.warning(
                "llm json-failure fallback detection fired (no structured error.code); "
                "body=%s",
                _truncate(text),
            )
            return LLMJsonValidationError(
                f"LLM request failed (400, json-failure fallback detection): {_truncate(text)}"
            )
    return LLMError(f"LLM request failed ({response.status_code}): {_truncate(text)}")


def _extract_content(data: dict[str, Any]) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected LLM response shape: {_truncate(repr(data))}") from exc
    if not isinstance(content, str):
        raise LLMError(f"LLM content is not a string: {_truncate(repr(content))}")
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
