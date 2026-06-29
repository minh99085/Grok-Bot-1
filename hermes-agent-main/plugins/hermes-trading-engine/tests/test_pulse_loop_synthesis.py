"""WS5 — loop-engine synthesis: read live performance, emit ranked next-experiment proposals.

Proves: a confidently-anti-predictive signal -> high-priority FADE proposal; a verifier that vetoes
winners -> high-priority verifier proposal; an outcome-proven dep-arb bucket -> Kelly proposal; a
starved directional funnel -> high-priority directional proposal; proposals are ranked high>med>low;
empty report yields nothing actionable. Advisory only (observe_only, auto_apply=False).
"""

from __future__ import annotations

from engine.pulse.loop_synthesis import synthesize, _deep_get, P_HIGH


def test_deep_get_finds_nested():
    assert _deep_get({"a": {"b": {"signal_edge": 42}}}, "signal_edge") == 42
    assert _deep_get({"x": [1, {"y": 7}]}, "y") == 7
    assert _deep_get({"a": 1}, "missing") is None


def test_anti_predictive_signal_becomes_high_priority_fade():
    rep = {"sections": {"external_signals": {"signal_edge": {
        "fade_candidates": [{"source": "grok_predictor", "context": "all", "n": 849,
                             "accuracy": 0.458, "wilson_hi": 0.49}],
        "follow_candidates": []}}}}
    out = synthesize(rep)
    assert out["observe_only"] is True and out["auto_apply"] is False
    fade = [p for p in out["proposals"] if p["area"] == "signals"]
    assert fade and fade[0]["priority"] == P_HIGH
    assert "FADE" in fade[0]["proposed_change"] and "grok_predictor" in fade[0]["proposed_change"]


def test_thin_fade_candidate_is_ignored():
    rep = {"signal_edge": {"fade_candidates": [{"source": "rsi", "context": "all", "n": 10,
                                                "accuracy": 0.2, "wilson_hi": 0.45}]}}
    assert [p for p in synthesize(rep)["proposals"] if p["area"] == "signals"] == []


def test_verifier_costing_edge_is_high_priority():
    rep = {"verifier": {"veto_quality": {"verdict": "vetoes_costing_edge", "n": 30,
                                         "vetoed_would_have_win_rate": 0.7,
                                         "vetoed_would_have_pnl_usd": 25.0}}}
    p = [x for x in synthesize(rep)["proposals"] if x["area"] == "verifier"]
    assert p and p[0]["priority"] == P_HIGH and "explore_approve" in p[0]["proposed_change"]


def test_proven_dep_arb_bucket_proposes_kelly():
    rep = {"dependency_arbitrage": {"outcome": {"calibration_by_entry_bucket": {
        "0.10-0.20": {"n": 40, "win_rate": 0.62, "profit_factor": 1.6}}}}}
    p = [x for x in synthesize(rep)["proposals"] if x["area"] == "dependency_arb"]
    assert p and "Kelly" in p[0]["proposed_change"]


def test_starved_directional_funnel_flagged():
    rep = {"candidate_lifecycle": {"created": 2572, "terminals": {"accepted": 0}}}
    p = [x for x in synthesize(rep)["proposals"] if x["area"] == "directional"]
    assert p and p[0]["priority"] == P_HIGH


def test_ranking_high_before_low():
    rep = {"signal_edge": {"fade_candidates": [{"source": "s", "context": "all", "n": 100,
                                                "accuracy": 0.4, "wilson_hi": 0.48}]},
           "verifier": {"veto_quality": {"verdict": "good_vetoes"}}}
    pr = synthesize(rep)["proposals"]
    assert pr[0]["priority"] == P_HIGH                  # high-priority fade ranked first
    assert pr[-1]["priority"] == "low"                 # good_vetoes low-priority last


def test_empty_report_no_action():
    out = synthesize({})
    assert out["proposal_count"] == 0 and "keep soaking" in out["summary"]
