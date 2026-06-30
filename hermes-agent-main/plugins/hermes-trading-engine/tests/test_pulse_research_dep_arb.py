"""Research loop dep-arb experiment block + dep-arb verifier settle grading."""

from __future__ import annotations

import json

from engine.pulse.dep_arb_verifier import ClaudeDepArbVerifier
from engine.pulse.research_loop import build_dep_arb_research_block, make_research_fn
from engine.pulse.engine import PulseEngine


def test_build_dep_arb_research_block_compact():
    report = {
        "dependency_arbitrage": {
            "enabled": True,
            "settled": 4,
            "executed": 3,
            "realized_profit_usd": -12.5,
            "rejected_by_reason": {"dep_arb_verifier_veto": 2},
            "booking": {"settled_n": 4, "capture_ratio": 0.04, "theoretical_settled_usd": 200},
            "experiments": {
                "nested_execute_enabled": False,
                "mid_exit_enabled": True,
                "mid_exit_horizon_s": 60,
                "grok_convergence_enabled": True,
                "mid_convergence": {"by_horizon": {"60": {"n": 8, "converged_rate": 1.0}}},
            },
        },
        "dep_arb_intel": {
            "grok_convergence": {"accuracy_60s": 0.75, "scored_60s": 4},
            "claude_verifier": {
                "veto_quality": {"verdict": "good_vetoes", "n": 3},
                "approved_settled": {"n": 2, "win_rate": 0.5},
            },
        },
    }
    block = build_dep_arb_research_block(report)
    assert block["booking"]["capture_ratio"] == 0.04
    assert block["experiments"]["mid_convergence_by_horizon"]["60"]["n"] == 8
    assert block["intel"]["grok_convergence_accuracy_60s"] == 0.75
    assert block["intel"]["verifier_veto_quality"]["verdict"] == "good_vetoes"
    assert "PULSE_DEPENDENCY_ARB_CONJUNCTION" in block["allowed_knobs"]


def test_research_fn_includes_dep_arb_block_and_filters_knobs():
    captured = {}

    def _chat(prompt, **kwargs):
        captured["prompt"] = prompt
        return json.dumps({
            "summary": "tighten dep-arb",
            "exploit_contexts": [],
            "avoid_contexts": [],
            "knob_recommendations": [
                {"knob": "PULSE_DEPENDENCY_ARB_MID_EXIT_ENABLED", "value": 1, "reason": "60s conv"},
                {"knob": "PULSE_FAKE_KNOB", "value": 1, "reason": "reject"},
            ],
            "new_lessons": [],
            "dep_arb_next_experiment": "enable mid-exit only when 60s rate>0.5",
        })

    fn = make_research_fn(chat=_chat)
    out = fn({"dependency_arbitrage": {"experiments": {}}, "dep_arb_intel": {}})
    assert "DEP_ARB_EXPERIMENTS" in captured["prompt"]
    assert out["dep_arb_next_experiment"].startswith("enable mid-exit")
    knobs = [k["knob"] for k in out["knob_recommendations"]]
    assert "PULSE_DEPENDENCY_ARB_MID_EXIT_ENABLED" in knobs
    assert "PULSE_FAKE_KNOB" not in knobs


def test_dep_arb_verifier_settle_grade_approved():
    dav = ClaudeDepArbVerifier(
        verify_fn=lambda p: {"approve": True, "max_size_fraction": 1.0,
                             "confidence": 0.8, "reason": "ok"},
        enabled=True,
    )
    dav.start()
    did = "dep_arb:p:c:conjunction_implication"
    dav.request(did, {"lane": "dependency_arbitrage"})
    dav._process_one()
    eng = object.__new__(PulseEngine)
    eng.dep_arb_verifier = dav
    eng.research_loop = None
    pos = {
        "decision_id": did,
        "won": True,
        "realized_profit_usd": 8.5,
        "verifier": {"approved": True, "pending": False},
    }
    PulseEngine._on_dep_arb_position_settled(eng, pos)
    rep = dav.report()
    assert rep["approved_settled"]["n"] == 1
    assert rep["approved_settled"]["pnl_usd"] == 8.5
    dav.stop()


def test_dep_arb_verifier_veto_counterfactual_grade():
    dav = ClaudeDepArbVerifier(
        verify_fn=lambda p: {"approve": False, "reason": "high entry"},
        enabled=True,
    )
    dav.start()
    did = "dep_arb:p:c:conjunction_implication"
    dav.request(did, {"lane": "dependency_arbitrage"})
    dav._process_one()
    eng = object.__new__(PulseEngine)
    eng.dep_arb_verifier = dav
    eng.research_loop = None
    eng.cfg = type("C", (), {"settle_grace_s": 0.0})()
    eng._dep_arb_verifier_pending = []
    eng._resolve_dep_arb_position = lambda p, now: (True, "test")

    PulseEngine._schedule_dep_arb_verifier_counterfactual(
        eng, did,
        {"parent_market_id": "m", "shares": 50.0, "cost_usd": 20.0, "entry_vwap": 0.4},
        close_ts=1000.0,
    )
    PulseEngine._grade_dep_arb_verifier_decisions(eng, now=1001.0)
    rep = dav.report()
    assert rep["veto_quality"]["n"] == 1
    assert rep["veto_quality"]["vetoed_would_have_win_rate"] == 1.0
    dav.stop()