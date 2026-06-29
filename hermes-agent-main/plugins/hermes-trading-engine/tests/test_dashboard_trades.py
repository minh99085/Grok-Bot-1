"""Tests for dep-arb dashboard trade aggregation and stats."""
from engine.pulse.dashboard_trades import (
    dep_arb_stats,
    dep_arb_trades_for_dashboard,
    recent_trades_for_dashboard,
)


def _sample_ledger():
    return {
        "positions": [],
        "accounting_state": {
            "dep_arb_ledger": {
                "positions": {
                    "643104": {
                        "parent_window_key": "643104",
                        "status": "settled",
                        "entry_ts": 1000.0,
                        "close_ts": 1900.0,
                        "entry_vwap": 0.54,
                        "realized_profit_usd": 1.16,
                        "expected_profit_usd": 2.31,
                        "won": True,
                        "outcome_settled": True,
                    },
                    "643152": {
                        "parent_window_key": "643152",
                        "status": "open",
                        "entry_ts": 2000.0,
                        "close_ts": 2900.0,
                        "entry_vwap": 0.541,
                        "expected_profit_usd": 2.77,
                    },
                    "643200": {
                        "parent_window_key": "643200",
                        "status": "settled",
                        "entry_ts": 900.0,
                        "close_ts": 1800.0,
                        "entry_vwap": 0.08,
                        "realized_profit_usd": -5.0,
                        "won": False,
                        "outcome_settled": True,
                    },
                }
            }
        },
    }


def test_dep_arb_trades_dashboard_only():
    ledger = _sample_ledger()
    rows = dep_arb_trades_for_dashboard(ledger, limit=20)
    assert len(rows) == 3
    assert all(r["trade_type"] == "dep_arb" for r in rows)
    assert rows[0]["parent_window_key"] if "parent_window_key" in rows[0] else True
    assert rows[0]["status"] == "open"
    assert rows[0]["side"] == "P-UP"
    settled = [r for r in rows if r["status"] == "settled"]
    assert any(r["won"] is True for r in settled)
    assert any(r["won"] is False for r in settled)


def test_dep_arb_stats_wins_losses_total():
    st = dep_arb_stats(_sample_ledger())
    assert st["total"] == 3
    assert st["wins"] == 1
    assert st["losses"] == 1
    assert st["open"] == 1
    assert st["settled"] == 2


def test_dep_arb_fills_dashboard_when_directional_empty():
    ledger = _sample_ledger()
    rows = dep_arb_trades_for_dashboard(ledger, limit=20)
    assert len(rows) == 3
    assert rows[0]["trade_type"] == "dep_arb"
    assert rows[0]["research"]["market_series"] == "parent 643152"
    assert rows[0]["pnl_usd"] is None
    win_row = next(r for r in rows if r.get("won") is True)
    assert win_row["pnl_usd"] == 1.16


def test_recent_trades_still_merges_all_lanes():
    ledger = {
        "positions": [
            {
                "side": "down",
                "entry_ts": 1500.0,
                "entry_price": 0.52,
                "status": "settled",
                "won": True,
                "pnl_usd": 2.5,
                "research": {"series_label": "15m"},
            }
        ],
        "accounting_state": {
            "dep_arb_ledger": {
                "positions": {
                    "w1": {
                        "parent_window_key": "w1",
                        "status": "settled",
                        "entry_ts": 2000.0,
                        "close_ts": 2100.0,
                        "entry_vwap": 0.5,
                        "realized_profit_usd": 1.0,
                        "won": True,
                    }
                }
            }
        },
    }
    rows = recent_trades_for_dashboard(ledger, limit=5)
    assert len(rows) == 2
    assert rows[0]["trade_type"] == "dep_arb"