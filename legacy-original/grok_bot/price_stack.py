"""Price feed stack: Binance + Coinbase + TradingView lead Chainlink settlement."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Protocol

from grok_bot.chainlink_reader import ChainlinkReader, ChainlinkSample
from grok_bot.reference_feeds import CexLeadingFeed, PriceSample, weighted_median
from loop.connectors.tradingview import TvSignal, TvSignalStore


@dataclass(frozen=True)
class LeadingSnapshot:
    price: float
    source_count: int
    sources: tuple[str, ...]
    confidence: float
    tv_direction: str | None = None
    tv_price: float | None = None
    freshness_ms: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceStackSnapshot:
    """Leading feeds are evaluated first; Chainlink is settlement truth only."""
    now_ms: int
    leading: LeadingSnapshot
    chainlink: ChainlinkSample | None
    window_start: float | None
    lead_vs_chainlink_bps: float | None
    lead_vs_window_bps: float | None
    implied_direction: str
    p_up: float
    edge_bps: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "now_ms": self.now_ms,
            "leading_price": self.leading.price,
            "leading_sources": list(self.leading.sources),
            "leading_confidence": self.leading.confidence,
            "tv_direction": self.leading.tv_direction,
            "chainlink_price": self.chainlink.price if self.chainlink else None,
            "chainlink_age_ms": self.chainlink.age_ms(self.now_ms) if self.chainlink else None,
            "window_start": self.window_start,
            "lead_vs_chainlink_bps": self.lead_vs_chainlink_bps,
            "lead_vs_window_bps": self.lead_vs_window_bps,
            "implied_direction": self.implied_direction,
            "p_up": self.p_up,
            "edge_bps": self.edge_bps,
        }


class CexFeedLike(Protocol):
    def samples(self, now_ms: int) -> list[PriceSample]: ...


def _tv_to_sample(tv: TvSignal) -> PriceSample | None:
    if tv.price is None or tv.price <= 0:
        return None
    return PriceSample(
        source="tradingview",
        price=tv.price,
        ts_ms=tv.received_ms,
        recv_ms=tv.received_ms,
        tier="leading",
    )


def blend_leading(
    cex_samples: list[PriceSample],
    tv: TvSignal | None,
    *,
    now_ms: int,
    max_staleness_ms: int = 5000,
    tv_max_age_ms: int = 120_000,
) -> LeadingSnapshot:
    fresh = [s for s in cex_samples if s.age_ms(now_ms) <= max_staleness_ms]
    tv_sample = None
    tv_dir = None
    tv_price = None
    if tv and (now_ms - tv.received_ms) <= tv_max_age_ms:
            tv_dir = tv.direction if tv.direction in ("UP", "DOWN") else None
            tv_price = tv.price
            tv_sample = _tv_to_sample(tv)

    pool = list(fresh)
    if tv_sample:
        pool.append(tv_sample)

    freshness = {s.source: s.age_ms(now_ms) for s in pool}
    if not pool:
        return LeadingSnapshot(float("nan"), 0, (), 0.0, tv_dir, tv_price, freshness)

    prices = [s.price for s in pool]
    weights = [
        (1.2 if s.source == "tradingview" else 1.0)
        * max(0.1, 1.0 - s.age_ms(now_ms) / max(max_staleness_ms, 1))
        for s in pool
    ]
    price = weighted_median(prices, weights)
    spread = (max(prices) - min(prices)) / price if price and len(prices) > 1 else 0.0
    count = len(pool)
    avg_age = sum(s.age_ms(now_ms) for s in pool) / count
    freshness_factor = max(0.0, 1.0 - avg_age / max(max_staleness_ms, 1))
    count_factor = min(1.0, count / 3.0)
    confidence = max(0.0, min(1.0, 0.45 * count_factor + 0.45 * freshness_factor - spread * 40))
    if tv_dir in ("UP", "DOWN"):
        confidence = min(1.0, confidence + 0.1)

    return LeadingSnapshot(
        price=price,
        source_count=count,
        sources=tuple(s.source for s in pool),
        confidence=confidence,
        tv_direction=tv_dir,
        tv_price=tv_price,
        freshness_ms=freshness,
    )


def _bps(lead: float, ref: float) -> float | None:
    if not ref or ref != ref or lead != lead:
        return None
    return ((lead - ref) / ref) * 10_000.0


def _sigmoid(x: float) -> float:
    x = max(-20.0, min(20.0, x))
    return 1.0 / (1.0 + math.exp(-x))


def estimate_p_up(
    *,
    window_start: float | None,
    leading: LeadingSnapshot,
    chainlink: ChainlinkSample | None,
) -> tuple[float, str, float]:
    """
    Edge model: leading stack vs window open (primary) and vs stale Chainlink (secondary).
    TradingView direction nudges p_up when price edge is thin.
    """
    ref = window_start or (chainlink.price if chainlink else None)
    if ref is None or not leading.price or leading.price != leading.price:
        return 0.5, "neutral", 0.0

    bps = _bps(leading.price, ref) or 0.0
    # ~8 bps ≈ meaningful move in a 5m BTC window at typical vol
    z = (bps / 8.0) * max(0.25, leading.confidence)
    if leading.tv_direction == "UP":
        z += 0.35 * leading.confidence
    elif leading.tv_direction == "DOWN":
        z -= 0.35 * leading.confidence

    p_up = _sigmoid(z)
    direction = "UP" if p_up >= 0.55 else "DOWN" if p_up <= 0.45 else "neutral"
    edge_bps = abs(bps) * leading.confidence
    return p_up, direction, edge_bps


class PriceStack:
    """Compose leading CEX + TradingView ahead of Chainlink settlement."""

    def __init__(
        self,
        cex: CexFeedLike,
        chainlink: ChainlinkReader,
        tv_store: TvSignalStore | None = None,
        *,
        max_cex_staleness_ms: int = 5000,
    ) -> None:
        self.cex = cex
        self.chainlink = chainlink
        self.tv_store = tv_store
        self.max_cex_staleness_ms = max_cex_staleness_ms

    def snapshot(
        self,
        now_ms: int,
        *,
        window_start: float | None = None,
        tv_symbol: str = "BTCUSDT",
    ) -> PriceStackSnapshot:
        cex_samples = self.cex.samples(now_ms)
        tv = self.tv_store.latest_for_symbol(tv_symbol) if self.tv_store else None
        leading = blend_leading(
            cex_samples,
            tv,
            now_ms=now_ms,
            max_staleness_ms=self.max_cex_staleness_ms,
        )
        chain = self.chainlink.read(now_ms)
        p_up, direction, edge_bps = estimate_p_up(
            window_start=window_start,
            leading=leading,
            chainlink=chain,
        )
        return PriceStackSnapshot(
            now_ms=now_ms,
            leading=leading,
            chainlink=chain,
            window_start=window_start,
            lead_vs_chainlink_bps=_bps(leading.price, chain.price) if chain else None,
            lead_vs_window_bps=_bps(leading.price, window_start) if window_start else None,
            implied_direction=direction,
            p_up=p_up,
            edge_bps=edge_bps,
        )