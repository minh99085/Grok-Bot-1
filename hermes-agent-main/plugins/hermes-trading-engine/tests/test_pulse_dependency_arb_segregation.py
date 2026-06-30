"""Dep-arb calibration segregation by constraint_type.

The negative-EV nested_implication heuristic must NOT poison the bucket-bleeding self-protection
for the positive-EV conjunction_implication (Fréchet floor) lane. These tests pin that conjunction
is judged on its OWN settled record, while aggregate stats (used by Kelly) still see everything,
and that legacy persisted state (no by_type) rebuilds the per-type record from positions.
"""
from __future__ import annotations

from engine.pulse.dependency_arb import (
    DependencyArbCalibration,
    DependencyArbLedger,
    dep_arb_bucket_bleeding,
)


def test_nested_bleed_does_not_block_conjunction():
    cal = DependencyArbCalibration()
    for _ in range(6):
        cal.record_settled(0.45, -5.0, False, constraint_type="nested_implication")
    # nested's own record is net-losing -> blocked
    blocked_n, reason_n = dep_arb_bucket_bleeding(
        0.45, cal, constraint_type="nested_implication")
    assert blocked_n is True and reason_n.startswith("bucket_bleeding_")
    # conjunction has no history in the same entry bucket -> NOT blocked
    blocked_c, _ = dep_arb_bucket_bleeding(
        0.45, cal, constraint_type="conjunction_implication")
    assert blocked_c is False
    # aggregate (no constraint_type) still sees the bleed (Kelly path / back-compat)
    blocked_agg, _ = dep_arb_bucket_bleeding(0.45, cal)
    assert blocked_agg is True


def test_by_type_tracks_each_constraint_separately():
    cal = DependencyArbCalibration()
    for _ in range(6):
        cal.record_settled(0.45, -5.0, False, constraint_type="nested_implication")
    for _ in range(6):
        cal.record_settled(0.45, 5.0, True, constraint_type="conjunction_implication")
    rep = cal.report()
    assert set(rep["by_type"]) == {"nested_implication", "conjunction_implication"}
    # conjunction's own record is winning -> not blocked; nested still blocked
    assert dep_arb_bucket_bleeding(0.45, cal, constraint_type="conjunction_implication")[0] is False
    assert dep_arb_bucket_bleeding(0.45, cal, constraint_type="nested_implication")[0] is True
    # aggregate mixes both: 6 wins of $5 vs 6 losses of $5 -> PF == 1.0 (not < 1.0) -> not blocked
    assert dep_arb_bucket_bleeding(0.45, cal)[0] is False


def test_record_without_constraint_type_only_updates_aggregate():
    cal = DependencyArbCalibration()
    for _ in range(6):
        cal.record_settled(0.45, -5.0, False)  # legacy call form, no type
    assert cal.by_type == {}
    assert dep_arb_bucket_bleeding(0.45, cal)[0] is True
    # with no per-type history, a typed query is never blocked
    assert dep_arb_bucket_bleeding(0.45, cal, constraint_type="conjunction_implication")[0] is False


def test_legacy_state_rebuilds_by_type_from_positions():
    """State persisted BEFORE segregation has aggregate `buckets` but no `by_type`; positions are
    the ground truth and must backfill the per-type record so nested stays blocked but conjunction
    (which never traded) is freed."""
    led = DependencyArbLedger(execute_enabled=True)
    positions = {}
    for i in range(6):
        positions["p%d" % i] = {
            "constraint_type": "nested_implication",
            "parent_window_key": "p%d" % i,
            "entry_vwap": 0.45, "shares": 10.0, "cost_usd": 4.5, "close_ts": 1.0,
            "status": "settled", "outcome_settled": True, "won": False,
            "realized_profit_usd": -4.5,
        }
    state = {
        "executed": 6, "settled": 6,
        "calibration": {  # legacy: aggregate only, NO by_type key
            "buckets": {"0.35-0.50": {
                "n": 6, "wins": 0, "win_rate": 0.0, "avg_pnl": -4.5,
                "profit_factor": 0.0, "gross_win": 0.0, "gross_loss": 27.0,
                "last_won": False}}},
        "positions": positions,
    }
    led.load_state(state)
    # by_type was empty on disk -> rebuilt from positions
    assert "nested_implication" in led.calibration.by_type
    assert dep_arb_bucket_bleeding(
        0.45, led.calibration, constraint_type="nested_implication")[0] is True
    assert dep_arb_bucket_bleeding(
        0.45, led.calibration, constraint_type="conjunction_implication")[0] is False


def test_to_state_round_trips_by_type():
    cal = DependencyArbCalibration()
    for _ in range(6):
        cal.record_settled(0.45, -5.0, False, constraint_type="nested_implication")
    cal2 = DependencyArbCalibration()
    cal2.load_state(cal.to_state())
    assert "nested_implication" in cal2.by_type
    assert dep_arb_bucket_bleeding(0.45, cal2, constraint_type="nested_implication")[0] is True
    assert dep_arb_bucket_bleeding(0.45, cal2, constraint_type="conjunction_implication")[0] is False
