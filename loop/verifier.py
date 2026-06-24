"""Independent checker — maker never grades its own work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reasons: list[str]
    evidence: dict[str, Any]


DEFAULT_RULES = {
    "min_sharpe": 1.5,
    "max_drawdown": 0.10,
    "min_newey_west_t": 2.0,
    "min_oos_years": 2.0,
}


def verify_signal(
    signal: dict[str, Any],
    *,
    rules: dict[str, float] | None = None,
) -> Verdict:
    """Pure-function verifier. All promotion gates are code-checked."""
    r = {**DEFAULT_RULES, **(rules or {})}
    reasons: list[str] = []
    evidence: dict[str, Any] = {}

    sharpe = float(signal.get("sharpe", 0.0))
    drawdown = float(signal.get("max_drawdown", 1.0))
    t_stat = float(signal.get("newey_west_t", 0.0))
    oos_years = float(signal.get("oos_years", 0.0))

    evidence.update(sharpe=sharpe, max_drawdown=drawdown, newey_west_t=t_stat, oos_years=oos_years)

    if sharpe < r["min_sharpe"]:
        reasons.append(f"sharpe {sharpe:.2f} < {r['min_sharpe']}")
    if drawdown > r["max_drawdown"]:
        reasons.append(f"drawdown {drawdown:.2%} > {r['max_drawdown']:.0%}")
    if t_stat < r["min_newey_west_t"]:
        reasons.append(f"newey_west_t {t_stat:.2f} < {r['min_newey_west_t']}")
    if oos_years < r["min_oos_years"]:
        reasons.append(f"oos_years {oos_years:.1f} < {r['min_oos_years']}")

    return Verdict(passed=not reasons, reasons=reasons, evidence=evidence)