"""Grok/xAI maker — proposes alpha context and risk overlay (never self-verifies)."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

XAI_URL = "https://api.x.ai/v1/chat/completions"

_SYSTEM = (
    "You are the MAKER for a paper-only Polymarket BTC 5-minute Up/Down bot. "
    "Propose risk context only. Respond with strict JSON: "
    '{"bias": "up|down|neutral", "confidence": 0-1, "size_hint": 0-1, "reason": "short"}'
)


@dataclass
class MakerDecision:
    called: bool
    bias: str = "neutral"
    confidence: float = 0.0
    size_hint: float = 1.0
    reason: str = ""
    latency_ms: int | None = None
    model: str | None = None
    zero_call_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def xai_chat(
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    timeout: float = 12.0,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    ).encode()
    req = urllib.request.Request(
        XAI_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "grok-bot-1/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode())
    return json.loads(payload["choices"][0]["message"]["content"])


class GrokMaker:
    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "grok-4.20-0309-non-reasoning",
        transport: Callable[[str, str, str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = bool(api_key)
        self.api_key = api_key
        self.model = model
        self._transport = transport or (
            lambda k, m, s, u: xai_chat(k, m, s, u)
        )

    def propose(self, ctx: dict[str, Any]) -> MakerDecision:
        if not self.enabled:
            return MakerDecision(called=False, zero_call_reason="no_xai_key")
        t0 = time.monotonic()
        try:
            raw = self._transport(self.api_key, self.model, _SYSTEM, json.dumps(ctx))
            return MakerDecision(
                called=True,
                bias=str(raw.get("bias", "neutral")).lower(),
                confidence=float(raw.get("confidence", 0)),
                size_hint=max(0.0, min(1.0, float(raw.get("size_hint", 1.0)))),
                reason=str(raw.get("reason", ""))[:200],
                latency_ms=int((time.monotonic() - t0) * 1000),
                model=self.model,
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001 — fail open for maker overlay
            return MakerDecision(
                called=False,
                zero_call_reason=str(exc)[:120],
            )