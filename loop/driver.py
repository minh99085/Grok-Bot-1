"""Five-stage discovery loop: ingest → signal → verify → execute → monitor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from loop.state import LoopState, StateManager
from loop.verifier import Verdict, verify_signal
from grok_bot.safety import submit_order


@dataclass
class CycleResult:
    stage: str
    ok: bool
    detail: str
    verdict: Verdict | None = None


@dataclass
class DiscoveryLoop:
    """Orchestrates the five sub-loops with maker-checker separation."""

    state_mgr: StateManager
    ingest: Callable[[], dict[str, Any]]
    propose: Callable[[dict[str, Any]], dict[str, Any] | None]
    max_drawdown: float = 0.05
    _positions: list[dict[str, Any]] = field(default_factory=list)

    def run_cycle(self) -> list[CycleResult]:
        results: list[CycleResult] = []
        state = self.state_mgr.read()

        # Stage 1: data ingestion
        try:
            data = self.ingest()
            results.append(CycleResult("ingest", True, "data_ready"))
        except Exception as exc:  # noqa: BLE001 — stage boundary
            results.append(CycleResult("ingest", False, str(exc)))
            self.state_mgr.write(state)
            return results

        # Stage 2: signal generation (maker — no self-grading)
        signal = self.propose(data)
        if signal is None:
            results.append(CycleResult("signal", True, "no_candidate"))
            state.windows_processed += 1
            self.state_mgr.write(state)
            return results
        results.append(CycleResult("signal", True, signal.get("name", "candidate")))

        # Stage 3: verification (checker — independent)
        verdict = verify_signal(signal)
        results.append(
            CycleResult(
                "verify",
                verdict.passed,
                "; ".join(verdict.reasons) or "passed",
                verdict=verdict,
            )
        )
        if not verdict.passed:
            state.last_verdict = "rejected"
            state.windows_processed += 1
            self.state_mgr.write(state)
            return results

        # Stage 4: execution (paper only)
        try:
            fill = submit_order(signal, paper=True)
            self._positions.append(fill)
            state.open_positions = list(self._positions)
            state.last_verdict = "executed"
            results.append(CycleResult("execute", True, "paper_fill"))
        except Exception as exc:  # noqa: BLE001
            results.append(CycleResult("execute", False, str(exc)))

        # Stage 5: risk monitoring
        dd = self._drawdown()
        if dd > self.max_drawdown:
            self._positions.clear()
            state.open_positions = []
            msg = f"drawdown {dd:.2%} > {self.max_drawdown:.0%}; positions closed"
            self.state_mgr.append_kill_event(msg)
            results.append(CycleResult("monitor", False, msg))
        else:
            results.append(CycleResult("monitor", True, f"drawdown {dd:.2%}"))

        state.windows_processed += 1
        if verdict.passed and dd <= self.max_drawdown:
            state.current_rung = "shadow"
        self.state_mgr.write(state)
        return results

    def _drawdown(self) -> float:
        if not self._positions:
            return 0.0
        pnl = sum(float(p.get("pnl", 0.0)) for p in self._positions)
        notional = sum(abs(float(p.get("notional", 1.0))) for p in self._positions) or 1.0
        return max(0.0, -pnl / notional)

    def discovery_status(self) -> dict[str, Any]:
        state = self.state_mgr.read()
        return {
            "rung": state.current_rung,
            "windows_processed": state.windows_processed,
            "last_verdict": state.last_verdict,
            "open_positions": len(state.open_positions),
            "kill_events": len(state.kill_events),
        }