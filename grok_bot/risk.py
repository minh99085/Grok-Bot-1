"""Stage-5 risk monitor — parallel kill-switch checks."""

from __future__ import annotations

from loop.state import StateManager


def risk_check(state_mgr: StateManager, *, max_drawdown_events: int = 3) -> dict:
    state = state_mgr.read()
    breached = len(state.kill_events) >= max_drawdown_events
    return {
        "ok": not breached,
        "kill_events": len(state.kill_events),
        "open_positions": len(state.open_positions),
        "rung": state.current_rung,
        "halt": breached,
    }