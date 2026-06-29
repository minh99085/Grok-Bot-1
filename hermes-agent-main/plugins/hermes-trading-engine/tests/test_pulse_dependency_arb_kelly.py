"""Lever C: outcome-settled dependency-arb P&L + Kelly sizing (default OFF)."""

from __future__ import annotations

from engine.pulse.markets import OrderBook, PulseWindow
from engine.pulse.dependency_arb import (
    DependencyArbCalibration,
    DependencyArbLedger,
    DependencyViolation,
    compute_dependency_arb_trade_usd,
    entry_price_bucket,
    outcome_settled_pnl,
    scan_nested_implication,
    try_execute_nested_implication,
)
from engine.pulse.walk_forward import passes_walk_forward


def _book(ask=0.10, depth_shares=50_000.0):
    return OrderBook(
        best_bid=ask - 0.02, best_ask=ask,
        asks=[(ask, depth_shares)], bids=[(ask - 0.02, depth_shares)],
        ask_depth_usd=ask * depth_shares, bid_depth_usd=(ask - 0.02) * depth_shares,
    )


def _windows(ask=0.42):
    t0 = 10_000_000.0
    parent = PulseWindow(
        event_id="p15", market_id="mp", slug="sp", title="15m",
        open_ts=t0, close_ts=t0 + 900, up_token_id="UP", down_token_id="DP",
        window_seconds=900, series_label="15m",
    )
    child = PulseWindow(
        event_id="c5", market_id="mc", slug="sc", title="5m",
        open_ts=t0 + 60, close_ts=t0 + 360, up_token_id="UC", down_token_id="DC",
        window_seconds=300, series_label="5m",
    )
    parent.up_book = _book(ask)
    parent.down_book = _book(0.55)
    child.up_book = _book(0.57)
    child.down_book = _book(0.40)
    return parent, child, t0


def _trade(parent, child, *, max_usd=50.0, **kwargs):
    vios = scan_nested_implication(parent, [child], epsilon=0.02)
    assert vios
    return try_execute_nested_implication(
        parent, child, vios[0], max_usd=max_usd, epsilon=0.02, **kwargs)


def _resolver(outcome_up: bool):
    def _resolve(pos, now):
        return bool(outcome_up), "test"
    return _resolve


def test_settle_due_books_real_win_and_loss():
    parent, child, t0 = _windows()
    trade = _trade(parent, child, max_usd=25.0)
    assert trade is not None
    shares = float(trade["shares"])
    cost = float(trade["cost_usd"])

    ledger = DependencyArbLedger(execute_enabled=True)
    ledger.book(trade, now=t0 + 100)

    ledger.settle_due(t0 + 901, resolver=_resolver(True))
    pos = ledger.positions["p15"]
    assert pos["won"] is True
    assert pos["realized_profit_usd"] == round(shares - cost, 6)
    assert pos["heuristic_profit_usd"] >= 0
    assert pos["outcome_settled"] is True

    ledger2 = DependencyArbLedger(execute_enabled=True)
    trade2 = _trade(parent, child, max_usd=25.0)
    ledger2.book(trade2, now=t0 + 100)
    ledger2.settle_due(t0 + 901, resolver=_resolver(False))
    pos2 = ledger2.positions["p15"]
    assert pos2["won"] is False
    assert pos2["realized_profit_usd"] == -cost
    assert pos2["realized_profit_usd"] < 0


def test_calibration_buckets_accumulate():
    cal = DependencyArbCalibration()
    for _ in range(3):
        cal.record_settled(0.08, 5.0, True)
    for _ in range(2):
        cal.record_settled(0.08, -10.0, False)
    stats = cal.bucket_stats(0.08)
    assert entry_price_bucket(0.08) == "0-0.10"
    assert stats["n"] == 5
    assert stats["wins"] == 3
    assert stats["win_rate"] == 0.6
    assert stats["profit_factor"] == round(15.0 / 20.0, 4)
    assert stats["avg_pnl"] == round((3 * 5.0 - 2 * 10.0) / 5, 6)


def test_kelly_disabled_uses_flat_max_usd():
    parent, child, _ = _windows()
    trade = _trade(parent, child, max_usd=50.0, kelly_enabled=False)
    assert trade is not None
    assert trade["trade_usd"] == 50.0


def test_kelly_cold_start_and_walk_forward_clamp_to_flat():
    parent, child, _ = _windows(ask=0.10)
    cal = DependencyArbCalibration()
    for _ in range(5):
        cal.record_settled(0.10, 2.0, True)

    trade_cold = _trade(
        parent, child, max_usd=50.0, kelly_enabled=True,
        kelly_fraction=0.25, calibration=cal, walk_forward_passed=True,
    )
    assert trade_cold is not None
    assert trade_cold["trade_usd"] == 50.0

    for _ in range(20):
        cal.record_settled(0.10, 2.0, True)
    trade_wf = _trade(
        parent, child, max_usd=50.0, kelly_enabled=True,
        kelly_fraction=0.25, calibration=cal, walk_forward_passed=False,
    )
    assert trade_wf is not None
    assert trade_wf["trade_usd"] == 50.0


def test_kelly_high_edge_sizes_up_negative_ev_zero():
    parent, child, _ = _windows(ask=0.10)
    cal = DependencyArbCalibration()
    for _ in range(25):
        cal.record_settled(0.10, 4.0, True)

    book = parent.up_book
    high = compute_dependency_arb_trade_usd(
        entry_vwap=0.10, max_usd=50.0, book=book,
        kelly_enabled=True, kelly_fraction=1.0, kelly_depth_frac=0.5,
        calibration=cal, walk_forward_passed=True,
    )
    assert 0 < high <= 50.0

    cal_bad = DependencyArbCalibration()
    for _ in range(25):
        cal_bad.record_settled(0.10, -10.0, False)
    neg = compute_dependency_arb_trade_usd(
        entry_vwap=0.10, max_usd=50.0, book=book,
        kelly_enabled=True, kelly_fraction=1.0, kelly_depth_frac=0.5,
        calibration=cal_bad, walk_forward_passed=True,
    )
    assert neg == 0.0


def test_trade_usd_respects_caps_and_no_upsize_after_loss():
    parent, child, _ = _windows(ask=0.10)
    cal = DependencyArbCalibration()
    for _ in range(25):
        cal.record_settled(0.10, 3.0, True)
    cal.record_settled(0.10, -5.0, False)

    book = parent.up_book
    depth_cap = book.ask_depth_usd * 0.5
    sized = compute_dependency_arb_trade_usd(
        entry_vwap=0.10, max_usd=50.0, book=book,
        kelly_enabled=True, kelly_fraction=1.0, kelly_depth_frac=0.5,
        calibration=cal, walk_forward_passed=True,
    )
    assert sized <= 50.0
    assert sized <= depth_cap
    assert sized == 50.0


def test_report_exposes_calibration_kelly_and_walk_forward():
    ledger = DependencyArbLedger(execute_enabled=True, kelly_enabled=False)
    positions = []
    t = 1_000_000.0
    for i in range(30):
        positions.append({
            "status": "settled", "entry_ts": t + i,
            "realized_profit_usd": 2.0 if i % 3 else -1.0,
            "won": i % 3 != 2,
            "entry_vwap": 0.08,
        })
    wf = passes_walk_forward(positions, min_holdout_n=5, min_holdout_pf=1.0)
    rep = ledger.report(walk_forward=wf)
    assert rep["paper_only"] is True
    assert rep["segregated_from_directional"] is True
    assert "dependency_arb_calibration" in rep
    assert rep["kelly_active"] is False
    assert rep["kelly_gate"]["walk_forward_passed"] == wf["passed"]


def test_outcome_settled_pnl_helper():
    trade = {"shares": 100.0, "cost_usd": 10.0}
    assert outcome_settled_pnl(trade, outcome_up=True) == 90.0
    assert outcome_settled_pnl(trade, outcome_up=False) == -10.0