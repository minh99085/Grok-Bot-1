"""Leading CEX price feeds — Binance and Coinbase (ahead of Chainlink oracle)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Callable, Sequence

LEADING_CEX_SOURCES = ("binance", "coinbase")

_LIVE_ENDPOINTS = {
    "binance": (
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        ("price",),
    ),
    "coinbase": (
        "https://api.coinbase.com/v2/prices/BTC-USD/spot",
        ("data", "amount"),
    ),
}


@dataclass(frozen=True)
class PriceSample:
    source: str
    price: float
    ts_ms: int
    recv_ms: int
    tier: str = "leading"

    def age_ms(self, now_ms: int) -> int:
        return max(0, now_ms - self.recv_ms)


def weighted_median(values: Sequence[float], weights: Sequence[float] | None = None) -> float:
    w = list(weights) if weights is not None else [1.0] * len(values)
    pairs = sorted(zip(values, w))
    total = sum(w)
    if total <= 0:
        return float("nan")
    acc = 0.0
    for v, wt in pairs:
        acc += wt
        if acc >= total / 2.0:
            return v
    return pairs[-1][0]


def _dig(obj: object, path: tuple[str | int, ...]) -> object:
    cur = obj
    for key in path:
        cur = cur[key]  # type: ignore[index]
    return cur


class CexLeadingFeed:
    """Read-only Binance + Coinbase basket. Failures drop individual sources."""

    def __init__(
        self,
        sources: Sequence[str] = LEADING_CEX_SOURCES,
        timeout: float = 3.0,
        transport: Callable[[str], dict] | None = None,
    ) -> None:
        self.sources = tuple(s for s in sources if s in _LIVE_ENDPOINTS)
        self.timeout = timeout
        self._transport = transport

    def samples(self, now_ms: int) -> list[PriceSample]:
        out: list[PriceSample] = []
        for src in self.sources:
            url, path = _LIVE_ENDPOINTS[src]
            try:
                if self._transport:
                    data = self._transport(url)
                else:
                    req = urllib.request.Request(url, headers={"User-Agent": "grok-bot-1/0.1"})
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                        data = json.loads(resp.read().decode())
                price = float(_dig(data, path))
                out.append(PriceSample(src, price, now_ms, now_ms, tier="leading"))
            except Exception:  # noqa: BLE001
                continue
        return out


class ScriptedCexFeed:
    def __init__(self, fn: Callable[[int], list[PriceSample]]) -> None:
        self._fn = fn

    def samples(self, now_ms: int) -> list[PriceSample]:
        return self._fn(now_ms)