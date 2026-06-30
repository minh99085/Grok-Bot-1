"""Dep-arb intel report block (Step 4 overnight soak readability)."""

from __future__ import annotations

from engine.pulse.dep_arb_intel import build_dep_arb_intel_report
from engine.pulse.research_loop import build_dep_arb_research_block


def test_build_dep_arb_intel_report_structure():
    rep = build_dep_arb_intel_report(
        grok_dependency={
            "dependency_proposals": 2,
            "deterministic_validated_dependencies": 1,
            "rejected_dependencies": [{"reason": "x"}],
            "accepted_dependencies": [{
                "constraint_type": "conjunction_implication",
                "parent_window_key": "p",
                "child_window_keys": ["c1", "c2"],
                "violation_magnitude": 0.12,
                "parent_up_mid": 0.4,
            }],
        },
        grok_screener={"enabled": True, "calls": 3, "proposals_cached": 2, "age_s": 45},
        grok_convergence={"enabled": True, "accuracy_60s": 0.8, "scored_60s": 5, "requested": 8},
        claude_verifier={
            "enabled": True,
            "verified": 4,
            "approvals": 2,
            "vetoes": 2,
            "approved_settled": {"n": 2, "win_rate": 0.5, "pnl_usd": 1.5},
            "veto_quality": {
                "verdict": "good_vetoes",
                "n": 2,
                "vetoed_would_have_win_rate": 0.0,
                "vetoed_would_have_pnl_usd": -4.0,
                "min_samples": 10,
            },
        },
    )
    assert rep["enabled"] is True
    assert rep["grok_proposals"]["validated"] == 1
    assert rep["grok_proposals"]["accepted_recent"][0]["constraint_type"] == "conjunction_implication"
    assert rep["grok_convergence"]["accuracy_60s"] == 0.8
    assert rep["claude_verifier"]["vetoes"] == 2
    assert rep["veto_quality"]["verdict"] == "good_vetoes"
    assert rep["veto_quality"]["ready_for_gate"] is False
    assert "Grok proposals" in rep["headline"]
    assert "veto_quality" in rep["note"] or "veto" in rep["note"].lower()


def test_research_block_reads_grok_proposals_and_veto_quality():
    report = {
        "dependency_arbitrage": {"experiments": {}},
        "dep_arb_intel": build_dep_arb_intel_report(
            grok_dependency={"dependency_proposals": 1, "deterministic_validated_dependencies": 1},
            grok_convergence={"enabled": True, "accuracy_60s": 0.6, "scored_60s": 3},
            claude_verifier={
                "enabled": True,
                "veto_quality": {"verdict": "insufficient_evidence", "n": 1},
                "approved_settled": {"n": 0},
            },
        ),
    }
    block = build_dep_arb_research_block(report)
    assert block["intel"]["grok_proposals_validated"] == 1
    assert block["intel"]["veto_quality_verdict"] == "insufficient_evidence"