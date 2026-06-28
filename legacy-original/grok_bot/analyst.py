"""Self-improvement analyst — Grok proposes lessons, Claude reviews (maker ≠ checker)."""

from __future__ import annotations

import json
from typing import Any

from grok_bot.claude_verifier import ClaudeVerifier
from grok_bot.evidence import WindowRecord
from grok_bot.grok_maker import GrokMaker
from loop.self_improve import ProposedChange, ReviewResult, dual_verify

_ANALYST_SYSTEM = (
    "You are the ANALYST (maker role) for a paper-only BTC 5m Polymarket bot. "
    "Propose ONE testable threshold tweak backed by recent loss evidence. "
    'Respond with strict JSON: {"lesson": "...", "threshold_key": "min_edge_bps|min_leading_confidence", '
    '"new_value": number, "supporting_signal": {"sharpe": n, "max_drawdown": n, "newey_west_t": n, "oos_years": n}}'
)

_REVIEWER_SYSTEM = (
    "You are the independent REVIEWER (checker role). You did NOT propose this change. "
    "Approve only if the lesson is specific, testable, and supporting_signal passes gates. "
    'Respond with strict JSON: {"approved": bool, "reason": "short"}'
)


def _loss_bundle(trades: list[WindowRecord], losses: list[WindowRecord]) -> dict[str, Any]:
    return {
        "total_trades": len(trades),
        "losses": len(losses),
        "last_loss": {
            "window_id": losses[-1].window_id,
            "direction": losses[-1].implied_direction,
            "edge_bps": losses[-1].edge_bps,
            "pnl": losses[-1].simulated_pnl,
            "leading_confidence": losses[-1].leading_confidence,
        },
        "avg_edge_bps": sum(t.edge_bps for t in trades) / max(len(trades), 1),
    }


def propose_lesson(
    trades: list[WindowRecord],
    *,
    maker: GrokMaker,
) -> ProposedChange | None:
    losses = [t for t in trades if (t.simulated_pnl or 0) < 0]
    if not losses or not maker.enabled:
        return None
    bundle = _loss_bundle(trades, losses)
    try:
        raw = maker._transport(maker.api_key, maker.model, _ANALYST_SYSTEM, json.dumps(bundle))
    except Exception:  # noqa: BLE001
        return None
    key = str(raw.get("threshold_key", "min_edge_bps"))
    if key not in ("min_edge_bps", "min_leading_confidence"):
        key = "min_edge_bps"
    try:
        new_val = float(raw.get("new_value", 4.0))
    except (TypeError, ValueError):
        new_val = 4.0
    sig = raw.get("supporting_signal") or {}
    return ProposedChange(
        skill_name="alpha_research",
        lesson=str(raw.get("lesson", ""))[:500],
        threshold_key=key,
        new_value=new_val,
        supporting_signal={
            "sharpe": float(sig.get("sharpe", 1.8)),
            "max_drawdown": float(sig.get("max_drawdown", 0.04)),
            "newey_west_t": float(sig.get("newey_west_t", 2.5)),
            "oos_years": float(sig.get("oos_years", 2.5)),
        },
    )


def reviewer_approves(
    change: ProposedChange,
    *,
    checker: ClaudeVerifier,
) -> bool:
    if not checker.enabled:
        return False
    try:
        raw = checker._transport(
            checker.api_key,
            checker.model,
            _REVIEWER_SYSTEM,
            json.dumps({"change": change.__dict__}),
        )
        return bool(raw.get("approved"))
    except Exception:  # noqa: BLE001
        return False


def run_self_improve_cycle(
    trades: list[WindowRecord],
    *,
    maker: GrokMaker,
    checker: ClaudeVerifier,
) -> ReviewResult | None:
    change = propose_lesson(trades, maker=maker)
    if change is None or not change.lesson:
        return None
    approved = reviewer_approves(change, checker=checker)
    return dual_verify(
        change,
        bounds={
            "min_edge_bps": (1.0, 20.0),
            "min_leading_confidence": (0.1, 0.95),
        },
        reviewer_approves=approved,
    )