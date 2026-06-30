"""Dep-arb experiment gates: nested-off, clock-skew, mid-convergence observer."""

from __future__ import annotations

from engine.pulse.markets import OrderBook, PulseWindow
from engine.pulse.dependency_arb import DependencyViolation
from types import SimpleNamespace

from engine.pulse.dependency_arb_experiments import (
    DepArbMidConvergenceObserver,
    apply_dep_arb_experiments,
    clock_skew_passes,
    execute_gate,
    gap_converged,
    try_mid_exit_positions,
)
from engine.pulse.dependency_arb import DependencyArbLedger


def _book(ask=0.45, *, ts=0.0):
    return OrderBook(
        best_bid=ask - 0.02, best_ask=ask,
        asks=[(ask, 10_000.0)], bids=[(ask - 0.02, 10_000.0)],
        ask_depth_usd=ask * 10_000, bid_depth_usd=(ask - 0.02) * 10_000,
        ts=ts,
    )


def _window(eid, *, open_ts, book_ts=None, ask=0.50):
    w = PulseWindow(
        event_id=eid, market_id="m", slug="s", title="t",
        open_ts=open_ts, close_ts=open_ts + 900,
        up_token_id="U", down_token_id="D",
        window_seconds=900, series_label="15m",
    )
    w.up_book = _book(ask, ts=book_ts if book_ts is not None else open_ts)
    w.down_book = _book(1.0 - ask, ts=book_ts if book_ts is not None else open_ts)
    return w


def _violation(ctype="nested_implication"):
    return DependencyViolation(
        constraint_type=ctype,
        parent_window_key="p15", child_window_keys=["c5"],
        description="test", parent_up_mid=0.42, child_up_mids=[0.57],
        violation_magnitude=0.05, actionable=True,
    )


def test_execute_gate_blocks_nested_when_disabled():
    v = _violation("nested_implication")
    ok, reason = execute_gate(v, nested_execute_enabled=False, clock_skew_enabled=False)
    assert ok is False and reason == "nested_execute_disabled_experiment"
    ok2, reason2 = execute_gate(
        _violation("conjunction_implication"),
        nested_execute_enabled=False, clock_skew_enabled=False,
    )
    assert ok2 is True and reason2 == "ok"


def test_clock_skew_requires_stale_parent_and_fresh_child():
    now = 10_000.0
    parent = _window("p15", open_ts=now - 300, book_ts=now - 30)
    child = _window("c5", open_ts=now - 60, book_ts=now - 10)
    ok, reason = clock_skew_passes(
        parent, child, now=now,
        min_parent_book_age_s=120, max_child_book_age_s=90, max_child_window_age_s=120,
    )
    assert ok is False and reason == "clock_skew_parent_book_too_fresh"
    parent.up_book = _book(0.42, ts=now - 150)
    ok2, reason2 = clock_skew_passes(
        parent, child, now=now,
        min_parent_book_age_s=120, max_child_book_age_s=90, max_child_window_age_s=120,
    )
    assert ok2 is True and reason2 == "ok"


def test_clock_skew_rejects_stale_child_book_and_old_window():
    now = 10_000.0
    parent = _window("p15", open_ts=now - 500, book_ts=now - 200)
    child_stale_book = _window("c5", open_ts=now - 60, book_ts=now - 200)
    ok, reason = clock_skew_passes(
        parent, child_stale_book, now=now,
        min_parent_book_age_s=120, max_child_book_age_s=90, max_child_window_age_s=120,
    )
    assert ok is False and reason == "clock_skew_child_book_too_stale"
    child_old_window = _window("c5", open_ts=now - 200, book_ts=now - 5)
    ok2, reason2 = clock_skew_passes(
        parent, child_old_window, now=now,
        min_parent_book_age_s=120, max_child_book_age_s=90, max_child_window_age_s=120,
    )
    assert ok2 is False and reason2 == "clock_skew_child_window_too_old"


def test_mid_convergence_observer_tracks_gap_decay():
    t0 = 10_000.0
    parent = _window("p15", open_ts=t0 - 200, book_ts=t0 - 150, ask=0.42)
    child = _window("c5", open_ts=t0 - 30, book_ts=t0 - 5, ask=0.57)
    obs = DepArbMidConvergenceObserver(horizons_s=(30.0, 60.0))
    v = _violation()
    obs.snap(v, parent=parent, child=child, now=t0)
    assert len(obs._pending) == 1
    child.up_book = _book(0.50, ts=t0 + 29)
    parent.up_book = _book(0.42, ts=t0 + 29)
    obs.advance([parent, child], now=t0 + 35)
    assert len(obs._pending) == 1
    child.up_book = _book(0.46, ts=t0 + 59)
    obs.advance([parent, child], now=t0 + 65)
    assert len(obs._pending) == 0
    rep = obs.report()
    assert rep["completed"] == 1
    assert rep["by_horizon"]["30"]["n"] == 1
    assert rep["by_horizon"]["60"]["n"] == 1
    assert rep["by_horizon"]["60"]["converged"] == 1


def test_mid_convergence_observer_state_roundtrip():
    obs = DepArbMidConvergenceObserver(horizons_s=(30.0,))
    t0 = 10_000.0
    parent = _window("p15", open_ts=t0 - 200, book_ts=t0 - 150, ask=0.42)
    child = _window("c5", open_ts=t0 - 30, book_ts=t0 - 5, ask=0.57)
    obs.snap(_violation(), parent=parent, child=child, now=t0)
    state = obs.to_state()
    obs2 = DepArbMidConvergenceObserver(horizons_s=(30.0,))
    obs2.load_state(state)
    assert len(obs2._pending) == 1
    key = next(iter(obs2._pending))
    assert obs2._pending[key].gap0 == obs._pending[key].gap0


def test_apply_dep_arb_experiments_disables_bleeding_nested():
    cfg = SimpleNamespace(
        dependency_arb_nested_execute=True,
        dependency_arb_clock_skew_enabled=False,
        dependency_arb_min_parent_book_age_s=120.0,
    )
    dep = {
        "dependency_arb_calibration": {
            "by_entry_bucket": {"0.35-0.50": {"n": 8, "profit_factor": 0.26}},
        },
        "experiments": {},
        "rejected_by_reason": {},
        "executed": 2,
    }
    applied = apply_dep_arb_experiments(cfg, dep)
    assert cfg.dependency_arb_nested_execute is False
    assert any("nested_execute=0" in a for a in applied)
    assert cfg.dependency_arb_clock_skew_enabled is True


def test_apply_dep_arb_experiments_low_mid_convergence():
    cfg = SimpleNamespace(
        dependency_arb_nested_execute=True,
        dependency_arb_clock_skew_enabled=True,
        dependency_arb_min_parent_book_age_s=120.0,
    )
    dep = {
        "dependency_arb_calibration": {"by_entry_bucket": {}},
        "experiments": {
            "mid_convergence": {
                "by_horizon": {"60": {"n": 12, "converged_rate": 0.15}},
            },
        },
        "rejected_by_reason": {},
        "executed": 0,
    }
    applied = apply_dep_arb_experiments(cfg, dep)
    assert cfg.dependency_arb_nested_execute is False
    assert any("low_mid_convergence" in a for a in applied)


def test_gap_converged():
    assert gap_converged(0.10, 0.04) is True
    assert gap_converged(0.10, 0.08) is False


def test_mid_exit_settles_converged_open_position():
    t0 = 10_000.0
    parent = _window("p15", open_ts=t0 - 200, book_ts=t0 - 150, ask=0.42)
    child = _window("c5", open_ts=t0 - 30, book_ts=t0 - 5, ask=0.57)
    parent.up_book.bids = [(0.44, 10_000.0)]
    child.up_book = _book(0.44, ts=t0 + 65)
    parent.up_book = _book(0.42, ts=t0 + 65)
    parent.up_book.bids = [(0.44, 10_000.0)]
    ledger = DependencyArbLedger(execute_enabled=True)
    ledger.positions["p15"] = {
        "status": "open", "entry_ts": t0, "child_window_key": "c5",
        "shares": 100.0, "cost_usd": 42.0, "entry_vwap": 0.42,
        "violation_magnitude": 0.15, "parent_window_key": "p15",
    }
    n = try_mid_exit_positions(
        ledger, {"p15": parent, "c5": child}, now=t0 + 65,
        horizon_s=60.0, enabled=True,
    )
    assert n == 1
    assert ledger.positions["p15"]["status"] == "settled"
    assert ledger.positions["p15"]["settlement_source"] == "mid_exit_convergence"
    assert ledger.positions["p15"]["realized_profit_usd"] > 0


def test_apply_enables_mid_exit_on_strong_convergence():
    cfg = SimpleNamespace(
        dependency_arb_nested_execute=False,
        dependency_arb_clock_skew_enabled=True,
        dependency_arb_min_parent_book_age_s=120.0,
        dependency_arb_mid_exit_enabled=False,
    )
    dep = {
        "dependency_arb_calibration": {"by_entry_bucket": {}},
        "experiments": {
            "mid_convergence": {
                "by_horizon": {"60": {"n": 8, "converged_rate": 0.875}},
            },
        },
        "rejected_by_reason": {},
        "executed": 0,
    }
    applied = apply_dep_arb_experiments(cfg, dep)
    assert cfg.dependency_arb_mid_exit_enabled is True
    assert any("mid_exit_enabled" in a for a in applied)