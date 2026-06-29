"""Tests for dashboard recent-trade aggregation."""
from engine.pulse.dashboard_trades import recent_trades_for_dashboard


def test_dep_arb_fills_dashboard_when_directional_empty():
    ledger = {
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
                    },
                    "643152": {
                        "parent_window_key": "643152",
                        "status": "open",
                        "entry_ts": 2000.0,
                        "close_ts": 2900.0,
                        "entry_vwap": 0.541,
                        "expected_profit_usd": 2.77,
                    },
                }
            }
        },
    }
    rows = recent_trades_for_dashboard(ledger, limit=20)
    assert len(rows) == 2
    assert rows[0]["trade_type"] == "dep_arb"
    assert rows[0]["side"] == "ARB"
    assert rows[0]["research"]["market_series"] == "nested 643152"
    assert rows[0]["status"] == "open"
    assert rows[0]["pnl_usd"] is None
    assert rows[1]["won"] is True
    assert rows[1]["pnl_usd"] == 1.16


def test_directional_and_dep_arb_merged_newest_first():
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
                    }
                }
            }
        },
    }
    rows = recent_trades_for_dashboard(ledger, limit=5)
    assert len(rows) == 2
    assert rows[0]["trade_type"] == "dep_arb"
    assert rows[1]["trade_type"] == "directional"