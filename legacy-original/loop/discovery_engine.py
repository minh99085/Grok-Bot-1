"""Profit discovery loop — bounded @goal until edge proven or budget exhausted."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from grok_bot.evidence import EvidenceStore, WindowRecord, promotion_rung
from loop.connectors.notifier import notify
from loop.driver import CycleResult, DiscoveryLoop
from loop.runner import run_goal
from loop.state import LoopState, StateManager


@dataclass
class DiscoveryConfig:
    max_windows: int = 500
    max_seconds: float = 86_400.0
    min_trades_arm: int = 20
    mode: str = "profit_discovery"


@dataclass
class DiscoveryRunOutcome:
    stop_reason: str
    windows_processed: int
    status: str
    headline: str
    discovery: dict[str, Any] = field(default_factory=dict)


class ProfitDiscoveryEngine:
    """
    North star: discover whether real edge exists — not deploy capital.
    Paper-only; resumes from STATE.md / state.json across restarts.
    """

    def __init__(
        self,
        *,
        loop: DiscoveryLoop,
        state_mgr: StateManager,
        evidence: EvidenceStore,
        config: DiscoveryConfig | None = None,
    ) -> None:
        self.loop = loop
        self.state_mgr = state_mgr
        self.evidence = evidence
        self.config = config or DiscoveryConfig()

    def status(self) -> dict[str, Any]:
        promo = promotion_rung(self.evidence.records, min_trades_arm=self.config.min_trades_arm)
        headline = self._headline(promo)
        return {
            "mode": self.config.mode,
            "status": promo["rung"],
            "headline": headline,
            "any_armed": promo["any_armed"],
            "blockers": promo["blockers"],
            "portfolio": promo["portfolio"],
            "calibration": promo["calibration"],
            "windows_processed": self.state_mgr.read().windows_processed,
        }

    def _headline(self, promo: dict[str, Any]) -> str:
        if promo["any_armed"]:
            return "EDGE FOUND — strategy reached armed rung under profit discovery gates"
        pf = promo["portfolio"]
        if pf["trades"]:
            return (
                f"profit discovery — {pf['trades']} paper trades, "
                f"PnL {pf['total_pnl']}, blockers: {', '.join(promo['blockers']) or 'none'}"
            )
        return "profit discovery — observe only, accumulating windows"

    def _persist_cycle(self, window_id: int, data: dict[str, Any], results: list[CycleResult]) -> None:
        state = self.state_mgr.read()
        action = "observe"
        pnl = None
        for r in results:
            if r.stage == "execute" and r.ok:
                action = "paper_fill"
            if r.stage == "verify" and not r.ok:
                action = "rejected"

        if action == "paper_fill":
            edge = float(data.get("edge_bps", 0)) / 10_000.0
            pnl = float(data.get("notional", 100)) * edge

        self.evidence.append(
            WindowRecord(
                window_id=window_id,
                ts_ms=int(data.get("ts_ms", int(time.time() * 1000))),
                p_up=float(data.get("p_up", 0.5)),
                edge_bps=float(data.get("edge_bps", 0)),
                implied_direction=str(data.get("implied_direction", "neutral")),
                action=action,
                simulated_pnl=pnl,
                tv_level=data.get("tv_level"),
                leading_confidence=float(data.get("leading_confidence", 0)),
            )
        )

        promo = promotion_rung(self.evidence.records, min_trades_arm=self.config.min_trades_arm)
        prev_rung = state.current_rung
        state.current_rung = promo["rung"]
        state.windows_processed = window_id + 1
        state.last_verdict = results[-1].detail if results else "pending"
        self.state_mgr.write(state)

        if promo["rung"] in ("shadow", "armed") and prev_rung != promo["rung"]:
            notify(f"Promotion: {prev_rung} → {promo['rung']}: {self._headline(promo)}", level="promotion")

    def condition(self) -> bool:
        return self.status()["any_armed"]

    def run(
        self,
        *,
        sleep: Callable[[float], None] = time.sleep,
        interval_seconds: float = 0.0,
    ) -> DiscoveryRunOutcome:
        state = self.state_mgr.read()
        start_window = state.windows_processed

        def step(i: int) -> None:
            window_id = start_window + i
            data = self.loop.ingest()
            results: list[CycleResult] = []

            try:
                results.append(CycleResult("ingest", True, "data_ready"))
                signal = self.loop.propose(data)
                if signal is None:
                    results.append(CycleResult("signal", True, "no_candidate"))
                    self._persist_cycle(window_id, data, results)
                    return
                results.append(CycleResult("signal", True, signal.get("name", "candidate")))
                from loop.verifier import verify_signal
                from grok_bot.safety import submit_order

                verdict = verify_signal(signal)
                results.append(CycleResult("verify", verdict.passed, "; ".join(verdict.reasons) or "passed", verdict))
                if not verdict.passed:
                    self._persist_cycle(window_id, data, results)
                    return
                fill = submit_order(signal, paper=True)
                self.loop._positions.append(fill)
                results.append(CycleResult("execute", True, "paper_fill"))
                dd = self.loop._drawdown()
                results.append(CycleResult("monitor", dd <= self.loop.max_drawdown, f"drawdown {dd:.2%}"))
            except Exception as exc:  # noqa: BLE001
                results.append(CycleResult("ingest", False, str(exc)))

            self._persist_cycle(window_id, data, results)
            if interval_seconds > 0:
                sleep(interval_seconds)

        ok, iters = run_goal(
            step,
            self.condition,
            max_iterations=self.config.max_windows,
            max_seconds=self.config.max_seconds,
        )
        final = self.status()
        state = self.state_mgr.read()

        if ok:
            stop_reason = "edge_proven"
            status = "armed"
        elif final["status"] == "armed":
            stop_reason = "edge_proven"
            status = "armed"
        else:
            stop_reason = "budget_exhausted"
            status = "no_edge_found" if final["portfolio"]["trades"] else "observe"

        state.current_rung = final["status"]
        state.last_verdict = stop_reason
        self.state_mgr.write(state)

        if status == "armed":
            notify(f"PROFIT DISCOVERY COMPLETE — {final['headline']}", level="armed")
        elif status == "no_edge_found":
            notify(f"NO EDGE FOUND — {final['headline']}", level="discovery")

        return DiscoveryRunOutcome(
            stop_reason=stop_reason,
            windows_processed=state.windows_processed,
            status=status,
            headline=final["headline"],
            discovery=final,
        )