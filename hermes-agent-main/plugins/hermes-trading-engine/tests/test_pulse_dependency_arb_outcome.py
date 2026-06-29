"""F1 — dependency-arb settles on the REAL parent-window outcome (books wins AND losses).

Proves: with an engine-style resolver, a buy_parent_up position books shares-cost when the parent
settles UP and -cost when it settles DOWN; the entry-price calibration accumulates real win/loss;
realized P&L can be negative; an unresolved outcome keeps the position open; and the legacy
heuristic path is preserved when no resolver is supplied (backward compatibility).
"""

from __future__ import annotations

from engine.pulse.dependency_arb import (DependencyArbLedger, DependencyArbCalibration,
                                          outcome_settled_profit_usd)


def _trade(parent_key="p1", entry=0.10, cost=50.0):
    shares = round(cost / entry, 4)
    return {"parent_window_key": parent_key, "parent_market_id": "m1", "side": "buy_parent_up",
            "shares": shares, "cost_usd": cost, "entry_vwap": entry,
            "violation_magnitude": 0.40, "implied_bound": entry + 0.40,
            "capture_frac": 0.5, "expected_profit_usd": shares * 0.40 * 0.5,
            "close_ts": 1000.0}


def test_outcome_settled_profit_signs():
    t = _trade(entry=0.10, cost=50.0)               # 500 shares
    assert outcome_settled_profit_usd(t, True) == round(500.0 - 50.0, 6)    # +450 win
    assert outcome_settled_profit_usd(t, False) == round(-50.0, 6)          # -50 loss
    assert outcome_settled_profit_usd(t, None) is None                      # unresolved


def test_resolver_books_real_win_and_loss():
    led = DependencyArbLedger(execute_enabled=True)
    led.book(_trade("win", entry=0.08, cost=50.0), now=0.0)     # 625 shares
    led.book(_trade("lose", entry=0.08, cost=50.0), now=0.0)

    def resolver(pos):
        return (True, "polymarket_resolution") if pos["parent_window_key"] == "win" \
            else (False, "rtds_chainlink_proxy")

    n = led.settle_due(2000.0, resolver=resolver)
    assert n == 2
    assert led.wins == 1 and led.losses == 1
    # +575 win and -50 loss -> net +525, and realized CAN be negative per trade
    assert led.positions["win"]["realized_profit_usd"] == 575.0
    assert led.positions["lose"]["realized_profit_usd"] == -50.0
    assert led.realized_outcome_profit_usd == 525.0
    rep = led.report()
    assert rep["outcome"]["outcome_settled_n"] == 2
    assert rep["outcome"]["losses"] == 1
    assert rep["outcome"]["calibration_by_entry_bucket"]["0.00-0.10"]["n"] == 2


def test_resolver_none_keeps_position_open():
    led = DependencyArbLedger(execute_enabled=True)
    led.book(_trade("pending"), now=0.0)
    n = led.settle_due(2000.0, resolver=lambda pos: (None, None))
    assert n == 0
    assert led.positions["pending"]["status"] == "open"
    assert led.settled == 0


def test_no_resolver_preserves_heuristic_path():
    led = DependencyArbLedger(execute_enabled=True)
    led.book(_trade("h", entry=0.10, cost=50.0), now=0.0)
    n = led.settle_due(2000.0)                       # no resolver -> legacy heuristic
    assert n == 1
    p = led.positions["h"]
    assert p["settle_mode"] == "heuristic"
    assert p["realized_profit_usd"] >= 0.0           # heuristic never books a loss
    assert led.outcome_settled == 0 and led.heuristic_settled == 1


def test_outcome_settlement_survives_restart():
    led = DependencyArbLedger(execute_enabled=True)
    led.book(_trade("lose", entry=0.08, cost=50.0), now=0.0)
    led.settle_due(2000.0, resolver=lambda pos: (False, "rtds_chainlink_proxy"))
    assert led.realized_outcome_profit_usd == -50.0
    led2 = DependencyArbLedger(execute_enabled=True)
    led2.load_state(led.to_state())
    assert led2.positions["lose"]["realized_profit_usd"] == -50.0
    assert led2.losses == 1 and led2.wins == 0
    assert led2.realized_outcome_profit_usd == -50.0
    assert led2.calibration.to_dict()["0.00-0.10"]["n"] == 1


def test_calibration_bucket_keys():
    cal = DependencyArbCalibration()
    assert cal.bucket_key(0.05) == "0.00-0.10"
    assert cal.bucket_key(0.49) == "0.35-0.50"
    assert cal.bucket_key(0.80) == "0.50-1.01"
