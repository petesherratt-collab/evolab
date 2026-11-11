from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
import urllib.error
import urllib.request


@dataclass(frozen=True)
class Completion:
    request_id: str
    model: str
    provider: str | None
    message: dict[str, Any]
    usage: dict[str, Any]
    finish_reason: str | None = None


class OpenRouterClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "openai/gpt-6.1-sol",
        timeout_seconds: int = 180,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not self._api_key:
            raise ValueError("OPENROUTER_API_KEY_MISSING")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_format: dict[str, Any] | None = None,
        max_tokens: int = 1400,
        seed: int | None = None,
    ) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "reasoning": {"effort": "medium"},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if response_format is not None:
            payload["response_format"] = response_format
            # Structured-output support is endpoint-specific on OpenRouter.
            payload["provider"] = {"require_parameters": True}
        if seed is not None:
            payload["seed"] = seed
        request = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://localhost/collective-intelligence-engineering",
                "X-Title": "Collective Intelligence Engineering Harness",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:2000]
            raise RuntimeError(f"OPENROUTER_HTTP_{exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OPENROUTER_NETWORK_ERROR: {exc.reason}") from exc
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OPENROUTER_RESPONSE_CHOICES_MISSING")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise RuntimeError("OPENROUTER_RESPONSE_MESSAGE_MISSING")
        return Completion(
            request_id=str(body.get("id", "")),
            model=str(body.get("model", self.model)),
            provider=body.get("provider"),
            message=message,
            usage=body.get("usage") if isinstance(body.get("usage"), dict) else {},
            finish_reason=(
                str(choices[0].get("finish_reason"))
                if choices[0].get("finish_reason") is not None
                else None
            ),
        )
