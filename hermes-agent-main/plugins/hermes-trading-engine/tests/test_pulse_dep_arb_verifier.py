"""Claude dep-arb verifier (conjunction-only maker-checker)."""

from __future__ import annotations

from engine.pulse.dep_arb_verifier import (
    ClaudeDepArbVerifier,
    build_dep_arb_verify_payload,
    shrink_dep_arb_trade,
)
from engine.pulse.dependency_arb import DependencyViolation


def test_should_verify_conjunction_only():
    v = ClaudeDepArbVerifier(enabled=True, conjunction_only=True, verify_fn=lambda p: None)
    assert v.should_verify("conjunction_implication") is True
    assert v.should_verify("nested_implication") is False


def test_build_payload_includes_lane_and_trade():
    viol = DependencyViolation(
        constraint_type="conjunction_implication",
        parent_window_key="p", child_window_keys=["c1", "c2"],
        description="t", parent_up_mid=0.40, child_up_mids=[0.55, 0.52],
        implied_bound=0.57, violation_magnitude=0.17,
    )
    trade = {"entry_vwap": 0.41, "cost_usd": 25.0, "shares": 60.0,
             "expected_profit_usd": 5.0, "violation_magnitude": 0.17}
    payload = build_dep_arb_verify_payload(viol, trade, experiments={"mid_exit_enabled": True})
    assert payload["lane"] == "dependency_arbitrage"
    assert payload["constraint_type"] == "conjunction_implication"
    assert payload["experiments"]["mid_exit_enabled"] is True


def test_build_payload_includes_grok_convergence_prior():
    viol = DependencyViolation(
        constraint_type="conjunction_implication",
        parent_window_key="p", child_window_keys=["c1"],
        description="t", parent_up_mid=0.40, child_up_mids=[0.55],
        implied_bound=0.55, violation_magnitude=0.15,
    )
    trade = {"entry_vwap": 0.41, "cost_usd": 10.0}
    grok_conv = {"converge_60s": 0.6, "hold_to_resolution_risk": "med", "pending": False}
    payload = build_dep_arb_verify_payload(viol, trade, grok_convergence=grok_conv)
    assert payload["grok_convergence_prior"]["converge_60s"] == 0.6


def test_shrink_trade_never_enlarges():
    trade = {"cost_usd": 50.0, "shares": 100.0, "expected_profit_usd": 10.0}
    out = shrink_dep_arb_trade(trade, 0.5)
    assert out["cost_usd"] == 25.0
    assert out["shares"] == 50.0
    assert out["verifier_size_fraction"] == 0.5


def test_dep_arb_verifier_grade_veto_counterfactual():
    dav = ClaudeDepArbVerifier(
        verify_fn=lambda p: {"approve": False, "reason": "bleed"},
        enabled=True,
    )
    dav.start()
    dav.request("dep_arb:p:c:conjunction_implication", {"lane": "dependency_arbitrage"})
    import time
    for _ in range(30):
        if dav.get("dep_arb:p:c:conjunction_implication"):
            break
        time.sleep(0.05)
    dav.grade("dep_arb:p:c:conjunction_implication", won=True, pnl=6.0, acted=False)
    rep = dav.report()
    assert rep["veto_quality"]["n"] == 1
    assert rep["veto_quality"]["vetoed_would_have_pnl_usd"] == 6.0
    dav.stop()


def test_verifier_veto_blocks_approve():
    def _veto(_payload):
        return {"approve": False, "max_size_fraction": 0.0, "confidence": 0.9, "reason": "high_entry"}

    dav = ClaudeDepArbVerifier(enabled=True, verify_fn=_veto, fail_open=False)
    dav.start()
    dav.request("dep_arb:p:c:conjunction_implication", {"lane": "dependency_arbitrage"})
    import time
    for _ in range(30):
        if dav.get("dep_arb:p:c:conjunction_implication"):
            break
        time.sleep(0.05)
    verdict = dav.verdict_or_failopen("dep_arb:p:c:conjunction_implication")
    assert verdict.get("approve") is False
    dav.stop()