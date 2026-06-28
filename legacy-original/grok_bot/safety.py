"""Paper-only safety lock — live order routing is structurally impossible."""

from __future__ import annotations

from typing import Any


class LiveTradingDisabledError(RuntimeError):
    pass


def submit_order(signal: dict[str, Any], *, paper: bool) -> dict[str, Any]:
    if not paper:
        raise LiveTradingDisabledError(
            "live order routing is disabled; Grok-Bot-1 is paper-only by design"
        )
    notional = float(signal.get("notional", 100.0))
    edge = float(signal.get("edge", 0.01))
    return {
        "paper": True,
        "symbol": signal.get("symbol", "unknown"),
        "notional": notional,
        "pnl": notional * edge,
        "signal": signal.get("name", "candidate"),
    }