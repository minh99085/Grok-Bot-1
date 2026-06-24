"""Window evidence store — profit discovery metrics (pure functions)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class WindowRecord:
    window_id: int
    ts_ms: int
    p_up: float
    edge_bps: float
    implied_direction: str
    action: str  # observe | paper_fill | rejected
    simulated_pnl: float | None = None
    tv_level: str | None = None
    leading_confidence: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: list[WindowRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                self._records.append(WindowRecord(**{k: v for k, v in d.items() if k in WindowRecord.__dataclass_fields__}))
            except (json.JSONDecodeError, TypeError):
                continue

    def append(self, record: WindowRecord) -> None:
        self._records.append(record)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.as_dict(), default=str) + "\n")

    @property
    def records(self) -> list[WindowRecord]:
        return list(self._records)

    def trade_records(self) -> list[WindowRecord]:
        return [r for r in self._records if r.action == "paper_fill" and r.simulated_pnl is not None]


def portfolio_metrics(records: list[WindowRecord]) -> dict[str, Any]:
    trades = [r for r in records if r.action == "paper_fill" and r.simulated_pnl is not None]
    if not trades:
        return {"trades": 0, "total_pnl": 0.0, "win_rate": None, "profit_factor": None, "avg_win": None, "avg_loss": None}
    pnls = [float(r.simulated_pnl) for r in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross_win = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    pf = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)
    return {
        "trades": len(trades),
        "total_pnl": round(sum(pnls), 6),
        "win_rate": round(len(wins) / len(trades), 4),
        "profit_factor": round(pf, 4) if pf != float("inf") else None,
        "avg_win": round(gross_win / len(wins), 6) if wins else None,
        "avg_loss": round(-gross_loss / len(losses), 6) if losses else None,
    }


def calibration_proxy(records: list[WindowRecord]) -> dict[str, Any]:
    """Brier-style proxy: how often implied_direction matched positive pnl."""
    scored = [r for r in records if r.action == "paper_fill" and r.simulated_pnl is not None]
    if len(scored) < 5:
        return {"n": len(scored), "brier_proxy": None, "armed": False}
    errors = []
    for r in scored:
        pred_up = r.p_up
        outcome_up = 1.0 if (r.simulated_pnl or 0) > 0 and r.implied_direction == "UP" else 0.0
        if r.implied_direction == "DOWN":
            pred_up = 1.0 - r.p_up
            outcome_up = 1.0 if (r.simulated_pnl or 0) > 0 else 0.0
        errors.append((pred_up - outcome_up) ** 2)
    brier = sum(errors) / len(errors)
    return {"n": len(scored), "brier_proxy": round(brier, 4), "armed": brier < 0.22 and len(scored) >= 20}


def promotion_rung(records: list[WindowRecord], *, min_trades_arm: int = 20) -> dict[str, Any]:
    pf = portfolio_metrics(records)
    cal = calibration_proxy(records)
    blockers: list[str] = []

    if pf["trades"] == 0:
        rung = "observe"
        blockers.append("no_paper_trades")
    elif pf["trades"] < min_trades_arm:
        rung = "shadow"
        blockers.append("insufficient_sample")
    elif (pf["total_pnl"] or 0) <= 0:
        rung = "shadow"
        blockers.append("total_pnl_not_positive")
    elif pf["profit_factor"] is not None and pf["profit_factor"] < 1.0:
        rung = "shadow"
        blockers.append("profit_factor_below_1")
    elif not cal.get("armed"):
        rung = "shadow"
        blockers.append("calibration_not_armed")
    else:
        rung = "armed"

    return {
        "rung": rung,
        "blockers": blockers,
        "portfolio": pf,
        "calibration": cal,
        "profit_discovery": True,
        "any_armed": rung == "armed",
    }