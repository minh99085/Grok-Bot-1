"""BTC up/down 5-minute Polymarket window math."""

from __future__ import annotations

from dataclasses import dataclass

WINDOW_MS = 300_000


@dataclass(frozen=True)
class MarketDescriptor:
    slug: str
    condition_id: str
    up_token_id: str
    down_token_id: str
    window_start_ms: int
    window_end_ms: int


def window_boundary(now_ms: int) -> int:
    return (now_ms // WINDOW_MS) * WINDOW_MS


def slug_for_boundary(start_ms: int, prefix: str = "btc-updown-5m-") -> str:
    return f"{prefix}{start_ms // 1000}"