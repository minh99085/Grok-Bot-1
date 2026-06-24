"""Compose ingest → maker → numeric verify → Claude check → execute."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from grok_bot.claude_verifier import ClaudeVerifier
from grok_bot.grok_maker import GrokMaker
from loop.connectors.tradingview import TvSignalStore
from loop.verifier import Verdict, verify_signal


@dataclass
class PipelineContext:
    market: dict[str, Any]
    tv_signal: dict[str, Any] | None
    maker: dict[str, Any] | None
    numeric_verdict: Verdict | None
    claude_review: dict[str, Any] | None


def build_signal_candidate(
    market: dict[str, Any],
    *,
    tv_store: TvSignalStore | None = None,
    maker: GrokMaker | None = None,
    symbol: str = "BTCUSDT",
) -> tuple[dict[str, Any] | None, PipelineContext]:
    tv = tv_store.latest_for_symbol(symbol) if tv_store else None
    ctx = PipelineContext(
        market=market,
        tv_signal=tv.as_dict() if tv else None,
        maker=None,
        numeric_verdict=None,
        claude_review=None,
    )

    base = {
        "name": "btc_5m_directional",
        "symbol": market.get("symbol", "btc-updown-5m"),
        "sharpe": float(market.get("sharpe", 0)),
        "max_drawdown": float(market.get("max_drawdown", 1)),
        "newey_west_t": float(market.get("newey_west_t", 0)),
        "oos_years": float(market.get("oos_years", 0)),
        "edge": float(market.get("edge", 0)),
        "notional": float(market.get("notional", 100)),
    }

    if tv and tv.direction in ("UP", "DOWN"):
        base["tv_level"] = tv.level
        base["tv_direction"] = tv.direction
        base["tv_indicator"] = tv.indicator

    if maker and maker.enabled:
        md = maker.propose({"market": market, "tv_signal": ctx.tv_signal})
        ctx.maker = {
            "called": md.called,
            "bias": md.bias,
            "confidence": md.confidence,
            "size_hint": md.size_hint,
            "reason": md.reason,
        }
        if md.called and md.size_hint <= 0:
            return None, ctx

    if base["sharpe"] <= 0 and not ctx.tv_signal:
        return None, ctx

    return base, ctx


def verify_with_checker(
    signal: dict[str, Any],
    ctx: PipelineContext,
    *,
    claude: ClaudeVerifier | None = None,
) -> tuple[Verdict, PipelineContext]:
    numeric = verify_signal(signal)
    ctx.numeric_verdict = numeric
    if not numeric.passed:
        return numeric, ctx

    if claude and claude.enabled:
        review = claude.review_signal(signal, evidence=numeric.evidence)
        ctx.claude_review = {
            "called": review.called,
            "approved": review.approved,
            "reasons": review.reasons,
        }
        if review.called and not review.approved:
            return Verdict(False, review.reasons or ["claude_rejected"], numeric.evidence), ctx

    return numeric, ctx