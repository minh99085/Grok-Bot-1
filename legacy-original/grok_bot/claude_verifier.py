"""Claude/Anthropic checker — independent LLM verifier (maker ≠ checker)."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

_SYSTEM = (
    "You are the CHECKER for a paper-only Polymarket BTC 5-minute bot. "
    "You did NOT generate the signal. Grade only against numeric evidence. "
    "Respond with strict JSON: "
    '{"approved": bool, "reasons": ["..."], "confidence": 0-1}'
)


@dataclass
class ClaudeReview:
    called: bool
    approved: bool = False
    reasons: list[str] = field(default_factory=list)
    confidence: float = 0.0
    latency_ms: int | None = None
    model: str | None = None
    zero_call_reason: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def anthropic_chat(
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    timeout: float = 20.0,
) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "max_tokens": 512,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "temperature": 0,
        }
    ).encode()
    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=body,
        method="POST",
        headers={
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
            "User-Agent": "grok-bot-1/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode())
    text = payload["content"][0]["text"]
    return json.loads(text)


class ClaudeVerifier:
    def __init__(
        self,
        *,
        api_key: str = "",
        model: str = "claude-sonnet-4-20250514",
        transport: Callable[[str, str, str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.enabled = bool(api_key)
        self.api_key = api_key
        self.model = model
        self._transport = transport or (
            lambda k, m, s, u: anthropic_chat(k, m, s, u)
        )

    def review_signal(self, signal: dict[str, Any], *, evidence: dict[str, Any]) -> ClaudeReview:
        if not self.enabled:
            return ClaudeReview(called=False, zero_call_reason="no_claude_key")
        t0 = time.monotonic()
        try:
            user = json.dumps({"signal": signal, "evidence": evidence, "rules": [
                "Sharpe > 1.5", "max_drawdown < 10%", "Newey-West t > 2.0", "OOS >= 2y"
            ]})
            raw = self._transport(self.api_key, self.model, _SYSTEM, user)
            reasons = [str(r) for r in raw.get("reasons", [])]
            return ClaudeReview(
                called=True,
                approved=bool(raw.get("approved")),
                reasons=reasons,
                confidence=float(raw.get("confidence", 0)),
                latency_ms=int((time.monotonic() - t0) * 1000),
                model=self.model,
                raw=raw,
            )
        except Exception as exc:  # noqa: BLE001 — checker fails closed
            return ClaudeReview(
                called=False,
                approved=False,
                reasons=[str(exc)[:120]],
                zero_call_reason=str(exc)[:120],
            )