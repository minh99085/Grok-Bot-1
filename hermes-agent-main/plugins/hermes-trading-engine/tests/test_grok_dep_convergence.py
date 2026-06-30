"""Grok 60s dep-arb convergence prior (parse, gate, grade)."""

from __future__ import annotations

import json

from engine.pulse.grok_dep_convergence import (
    GrokDepConvergencePrior,
    build_convergence_context,
    convergence_prior_passes_gate,
    neutral_prior,
    parse_convergence_response,
    violation_prior_key,
)
from engine.pulse.dependency_arb import DependencyViolation
from engine.pulse.markets import OrderBook, PulseWindow


def test_parse_convergence_response():
    raw = json.dumps({
        "converge_60s": 0.72,
        "hold_to_resolution_risk": "low",
        "reason": "tight books",
    })
    out = parse_convergence_response(raw)
    assert out is not None
    assert out["converge_60s"] == 0.72
    assert out["hold_to_resolution_risk"] == "low"
    assert out["pending"] is False


def test_convergence_gate_fail_open_on_pending():
    ok, reason = convergence_prior_passes_gate(neutral_prior())
    assert ok is True
    assert reason == "no_prior_fail_open"


def test_convergence_gate_blocks_low_prior():
    prior = {"pending": False, "converge_60s": 0.2, "hold_to_resolution_risk": "med"}
    ok, reason = convergence_prior_passes_gate(prior, min_converge_60s=0.35)
    assert ok is False
    assert "grok_convergence_low_60s" in reason


def test_convergence_gate_blocks_high_hold_risk():
    prior = {"pending": False, "converge_60s": 0.8, "hold_to_resolution_risk": "high"}
    ok, reason = convergence_prior_passes_gate(prior)
    assert ok is False
    assert reason == "grok_hold_risk_high"


def _win(eid, ask=0.50, *, ws=300):
    w = PulseWindow(
        event_id=eid, market_id="m", slug="s", title="t",
        open_ts=1e7, close_ts=1e7 + ws, up_token_id="U", down_token_id="D",
        window_seconds=ws, series_label="5m" if ws < 600 else "15m",
    )
    w.up_book = OrderBook(best_bid=ask - 0.02, best_ask=ask,
                          asks=[(ask, 1000)], bids=[(ask - 0.02, 1000)])
    return w


def test_build_convergence_context_and_key():
    parent = _win("p", 0.40, ws=900)
    child = _win("c", 0.55, ws=300)
    viol = DependencyViolation(
        constraint_type="conjunction_implication",
        parent_window_key="p", child_window_keys=["c1", "c2"],
        description="t", parent_up_mid=0.40, child_up_mids=[0.55, 0.52],
        implied_bound=0.57, violation_magnitude=0.17, actionable=True,
    )
    ctx = build_convergence_context(viol, parent, child, now=1e7 + 100)
    assert ctx["gap"] == 0.15
    assert ctx["constraint_type"] == "conjunction_implication"
    assert violation_prior_key(viol) == "grok_conv:p:c1:conjunction_implication"


def test_grade_vs_observer_60s():
    def _predict(_ctx):
        return {
            "observe_only": True,
            "converge_60s": 0.8,
            "hold_to_resolution_risk": "low",
            "reason": "test",
            "pending": False,
        }

    prior = GrokDepConvergencePrior(predict_fn=_predict)
    prior.start()
    key = "grok_conv:p:c:conjunction_implication"
    prior.request(key, {"gap": 0.1})
    import time
    for _ in range(40):
        if not prior.get(key).get("pending"):
            break
        time.sleep(0.05)
    prior.grade(key, converged_60s=True)
    assert prior.scored == 1
    assert prior.correct_60s == 1
    prior.stop()