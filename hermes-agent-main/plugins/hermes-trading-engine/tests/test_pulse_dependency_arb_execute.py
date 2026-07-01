"""WS4: dependency-arb validator, paper execute, and segregated ledger."""

from __future__ import annotations

from engine.pulse.markets import OrderBook, PulseWindow
from engine.pulse.dependency_arb import (
    DependencyArbCalibration,
    DependencyArbLedger,
    DependencyViolation,
    dep_arb_bucket_bleeding,
    enrich_vwap_actionable,
    realized_dependency_profit_usd,
    validate_violation,
    try_execute_nested_implication,
    scan_nested_implication,
)


def _book(ask=0.45):
    return OrderBook(
        best_bid=ask - 0.02, best_ask=ask,
        asks=[(ask, 10_000.0)], bids=[(ask - 0.02, 10_000.0)],
        ask_depth_usd=ask * 10_000, bid_depth_usd=(ask - 0.02) * 10_000,
    )


def test_validate_rejects_invalid_llm_proposal():
    v = DependencyViolation(
        constraint_type="nested_implication",
        parent_window_key="p", child_window_keys=["c"],
        description="bogus", parent_up_mid=0.55, child_up_mids=[0.50],
        violation_magnitude=0.0,
    )
    ok, reason = validate_violation(v)
    assert ok is False and reason == "no_magnitude"
    v2 = DependencyViolation(
        constraint_type="grok_guess",
        parent_window_key="p", child_window_keys=["c"],
        description="llm", violation_magnitude=0.05,
    )
    ok2, reason2 = validate_violation(v2)
    assert ok2 is False and reason2 == "unsupported_constraint"


def test_paper_execute_and_settle_dependency_ledger():
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
    parent.up_book = _book(0.42)
    parent.down_book = _book(0.55)
    child.up_book = _book(0.57)
    child.down_book = _book(0.40)
    vios = scan_nested_implication(parent, [child], epsilon=0.02)
    assert len(vios) >= 1
    v = vios[0]
    assert validate_violation(v)[0] is True
    trade = try_execute_nested_implication(parent, child, v, max_usd=25.0, epsilon=0.02)
    assert trade is not None and trade["expected_profit_usd"] > 0
    ledger = DependencyArbLedger(execute_enabled=True)
    assert ledger.book(trade, now=t0 + 100) is True
    assert ledger.executed == 1 and ledger.has_open("p15")
    n = ledger.settle_due(t0 + 901)
    assert n == 1
    assert ledger.settled == 1
    assert ledger.realized_profit_usd > 0
    rep = ledger.report()
    assert rep["segregated_from_directional"] is True
    assert rep["strategy"] == "dependency_arbitrage"


def test_vwap_enrichment_rejection_reason():
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
    parent.up_book = OrderBook(best_bid=0.40, best_ask=0.42, asks=[(0.42, 1.0)],
                               bids=[(0.40, 1000.0)])
    parent.down_book = _book(0.55)
    child.up_book = _book(0.57)
    child.down_book = _book(0.40)
    vios = scan_nested_implication(parent, [child], epsilon=0.02, vwap_enrich=True)
    assert len(vios) >= 1
    v = enrich_vwap_actionable(vios[0], parent, child, max_usd=25.0, epsilon=0.02)
    assert v.actionable is False
    assert v.reason in ("partial_fill", "vwap_not_executable", "below_epsilon", "zero_shares")
    ledger = DependencyArbLedger(execute_enabled=False)
    ledger.record_scan(vios)
    assert ledger.rejected_by_reason


def test_vwap_enrichment_marks_actionable():
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
    parent.up_book = _book(0.42)
    child.up_book = _book(0.57)
    vios = scan_nested_implication(parent, [child], epsilon=0.02, vwap_enrich=True)
    assert vios and vios[0].actionable is True
    assert vios[0].reason == "vwap_executable"


def test_load_state_recomputes_capped_settled_pnl():
    ledger = DependencyArbLedger(execute_enabled=True)
    ledger.positions["p1"] = {
        "status": "settled",
        "shares": 5000.0,
        "entry_vwap": 0.01,
        "cost_usd": 50.0,
        "violation_magnitude": 0.47,
        "expected_profit_usd": 1175.0,
        "close_ts": 1.0,
    }
    ledger.realized_profit_usd = 1175.0
    ledger.settled = 1
    ledger.load_state(ledger.to_state())
    assert ledger.realized_profit_usd < 1175.0
    assert ledger.realized_profit_usd == round(50.0 * 0.47 * 0.5, 6)
    assert ledger.report()["booking"]["capture_ratio"] is not None


def test_realized_profit_capped_below_theoretical_on_low_entry():
    trade = {
        "shares": 5000.0,
        "entry_vwap": 0.01,
        "cost_usd": 50.0,
        "violation_magnitude": 0.47,
        "implied_bound": 0.48,
        "capture_frac": 0.5,
        "expected_profit_usd": 1175.0,
    }
    booked = realized_dependency_profit_usd(trade)
    assert booked < trade["expected_profit_usd"]
    assert booked == round(50.0 * 0.47 * 0.5, 6)


def test_execute_disabled_does_not_book():
    ledger = DependencyArbLedger(execute_enabled=False)
    trade = {"parent_window_key": "x", "close_ts": 1.0, "expected_profit_usd": 1.0}
    assert ledger.book(trade, now=0.0) is False
    assert ledger.executed == 0


def test_min_entry_vwap_floor_config_env(monkeypatch):
    from engine.pulse.engine import PulseConfig
    # Default: floor disabled (0.0) => no behavior change.
    assert PulseConfig().dependency_arb_min_entry_vwap == 0.0
    # from_env with no override stays disabled.
    monkeypatch.delenv("PULSE_DEPENDENCY_ARB_MIN_ENTRY_VWAP", raising=False)
    assert PulseConfig.from_env().dependency_arb_min_entry_vwap == 0.0
    # Operator sets the floor => picked up by from_env.
    monkeypatch.setenv("PULSE_DEPENDENCY_ARB_MIN_ENTRY_VWAP", "0.50")
    assert PulseConfig.from_env().dependency_arb_min_entry_vwap == 0.50


def _dep_arb_engine(tmp_path, min_floor):
    """Engine wired for a single nested-implication dep-arb violation at entry_vwap ~0.42."""
    from engine.pulse.price import PulsePriceFeed
    from engine.pulse.fair_value import RollingVol
    from engine.pulse.engine import PulseEngine, PulseConfig
    t0 = 10_000_000.0
    parent = PulseWindow(
        event_id="p15", market_id="mp", slug="btc-up-or-down-15m", title="15m",
        open_ts=t0, close_ts=t0 + 900, up_token_id="UP", down_token_id="DP",
        window_seconds=900, series_label="15m")
    child = PulseWindow(
        event_id="c5", market_id="mc", slug="btc-up-or-down-5m", title="5m",
        open_ts=t0 + 60, close_ts=t0 + 360, up_token_id="UC", down_token_id="DC",
        window_seconds=300, series_label="5m")
    parent.up_book = _book(0.42)   # entry_vwap ~0.42: below a 0.50 floor, below the 0.52 cap
    parent.down_book = _book(0.55)
    child.up_book = _book(0.60)    # child UP mid >> parent UP mid => nested violation
    child.down_book = _book(0.37)

    class _Mkt:
        def active_windows(self, now=None, **kw):
            return [parent, child]

        def hydrate_books(self, w):
            return w

        def fetch_resolution(self, market_id):
            return True

    feed = PulsePriceFeed(fetcher=lambda: 64000.0, source_name="rtds_chainlink",
                          vol=RollingVol(window_s=900, min_samples=2), max_open_lag_s=9999.0)
    cfg = PulseConfig(
        tick_seconds=1.0, data_dir=str(tmp_path), tradingview_webhook_port=0,
        dependency_arb_enabled=True, dependency_arb_execute_enabled=True,
        dependency_arb_nested_execute=True, dep_arb_verifier_enabled=False,
        dependency_arb_epsilon=0.02, dependency_arb_max_entry_vwap=0.52,
        dependency_arb_min_entry_vwap=min_floor)
    eng = PulseEngine(cfg, market_feed=_Mkt(), price_feed=feed)
    return eng, parent, child, t0


def test_min_entry_vwap_floor_gate_rejects_cheap_entry(tmp_path):
    # Floor OFF (0.0): the cheap-entry nested trade is NOT floor-rejected and books.
    eng0, parent, child, t0 = _dep_arb_engine(tmp_path, min_floor=0.0)
    eng0._scan_dependency_arb([parent, child], now=t0 + 100)
    assert eng0.dep_arb_ledger.rejected_by_reason.get("entry_vwap_below_floor", 0) == 0
    assert eng0.dep_arb_ledger.executed >= 1

    # Floor 0.50: the same entry_vwap ~0.42 trade is rejected by the floor and does not book.
    eng1, parent1, child1, t1 = _dep_arb_engine(tmp_path, min_floor=0.50)
    eng1._scan_dependency_arb([parent1, child1], now=t1 + 100)
    assert eng1.dep_arb_ledger.rejected_by_reason.get("entry_vwap_below_floor", 0) >= 1
    assert eng1.dep_arb_ledger.executed == 0


def test_dep_arb_bucket_bleeding_halts_losing_bucket():
    cal = DependencyArbCalibration()
    for _ in range(5):
        cal.record_settled(0.40, -10.0, False)
    halted, reason = dep_arb_bucket_bleeding(0.40, cal)
    assert halted is True and "0.35-0.50" in reason
    cal2 = DependencyArbCalibration()
    for _ in range(5):
        cal2.record_settled(0.40, 5.0, True)
    assert dep_arb_bucket_bleeding(0.40, cal2)[0] is False