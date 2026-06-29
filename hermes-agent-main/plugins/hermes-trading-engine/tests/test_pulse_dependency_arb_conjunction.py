"""WS3-B — economically-correct multi-child conjunction constraint (Fréchet floor).

Proves: 'all nested 5m children UP => 15m UP' yields P(up_15m) >= sum(child_up) - (n-1); a 15m up-mid
below that floor is a real violation (buy parent-UP); the floor rarely binds (mid children -> no
signal); the validator accepts/rejects on the bound; scan_windows only emits it when enabled; and the
single-child heuristic is NOT a hard constraint (kept separate, default behavior unchanged).
"""

from __future__ import annotations

from engine.pulse.dependency_arb import (scan_conjunction_implication, scan_windows,
                                          validate_violation, try_execute_nested_implication,
                                          DependencyViolation)
from engine.pulse.markets import OrderBook, PulseWindow


def _book(ask, *, depth=100000.0):
    bid = max(0.01, ask - 0.02)
    return OrderBook(best_bid=bid, best_ask=ask, ask_depth_usd=depth, bid_depth_usd=depth,
                     asks=[(ask, depth / ask)], bids=[(bid, depth / bid)])


def _win(eid, ws, *, up_ask):
    w = PulseWindow(event_id=eid, market_id="m" + eid, slug="s", title="t",
                    open_ts=0.0, close_ts=float(ws), up_token_id="U" + eid, down_token_id="D" + eid,
                    window_seconds=ws)
    w.up_book = _book(up_ask)
    return w


def _parent_children(parent_ask, child_asks):
    parent = _win("p15", 900, up_ask=parent_ask)
    children = [_win("c%d" % i, 300, up_ask=a) for i, a in enumerate(child_asks)]
    return parent, children


def test_conjunction_floor_violation_detected():
    # children all expensive (~0.85 mid) -> floor = 3*0.85 - 2 = 0.55; parent cheap (~0.40) -> violation
    parent, children = _parent_children(0.41, [0.86, 0.86, 0.86])   # mids ~0.40, ~0.85
    vios = scan_conjunction_implication(parent, children, epsilon=0.02, vwap_enrich=False)
    assert len(vios) == 1
    v = vios[0]
    assert v.constraint_type == "conjunction_implication"
    assert len(v.child_window_keys) == 3                      # ALL children, not collapsed to [0]
    assert v.implied_bound > v.parent_up_mid and v.violation_magnitude > 0
    assert validate_violation(v) == (True, "ok")


def test_floor_does_not_bind_for_mid_children():
    # mid children (~0.50) -> floor = 1.5 - 2 = -0.5 -> never below a real parent mid -> no signal
    parent, children = _parent_children(0.50, [0.51, 0.51, 0.51])
    assert scan_conjunction_implication(parent, children, epsilon=0.02, vwap_enrich=False) == []


def test_validator_rejects_unviolated_conjunction():
    v = DependencyViolation(constraint_type="conjunction_implication", parent_window_key="p",
                            child_window_keys=["a", "b"], description="x",
                            parent_up_mid=0.6, child_up_mids=[0.5, 0.5], implied_bound=0.5,
                            violation_magnitude=0.1)
    ok, reason = validate_violation(v)
    assert ok is False and reason == "conjunction_bound_not_violated"


def test_scan_windows_gating():
    parent, children = _parent_children(0.41, [0.86, 0.86, 0.86])
    windows = [parent] + children
    off = scan_windows(windows, epsilon=0.02, vwap_enrich=False, conjunction_enabled=False)
    on = scan_windows(windows, epsilon=0.02, vwap_enrich=False, conjunction_enabled=True)
    assert not any(v.constraint_type == "conjunction_implication" for v in off)
    assert any(v.constraint_type == "conjunction_implication" for v in on)


def test_conjunction_violation_is_executable_buy_parent_up():
    parent, children = _parent_children(0.41, [0.86, 0.86, 0.86])
    vios = scan_conjunction_implication(parent, children, epsilon=0.02, vwap_enrich=False)
    trade = try_execute_nested_implication(parent, children[0], vios[0], max_usd=25.0, epsilon=0.02)
    assert trade is not None and trade["side"] == "buy_parent_up"
    assert trade["constraint_type"] == "conjunction_implication" and trade["shares"] > 0
