"""Loop-engine synthesis (WS5) — read live performance, emit the next minimal experiment.

This is the deterministic core of the "self-improving quant loop" the project is built around
(AGENTS.md quant-team mandate: read live performance -> hypothesize -> propose a minimal gate/strategy
change -> measure on a soak). It ingests the published light report (which now carries the signal-edge
verdicts, dep-arb outcome calibration, risk-free arb capture stats and the verifier veto-quality from
this session's work) and emits a PRIORITIZED, structured list of advisory proposals.

ADVISORY ONLY: every proposal is paper-only, auto_apply=False, and names the evidence gate that would
justify acting. It NEVER changes config or places a trade. Deterministic + testable on purpose — the
loop's hypotheses should be reproducible, not an opaque LLM guess (an LLM can narrate them, but the
triggers live here).
"""

from __future__ import annotations

from typing import Any, Optional

P_HIGH, P_MED, P_LOW = "high", "medium", "low"


def _deep_get(obj: Any, key: str) -> Optional[Any]:
    """First occurrence of ``key`` anywhere in a nested dict/list (report sections move around)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _deep_get(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _deep_get(v, key)
            if found is not None:
                return found
    return None


def _proposal(priority, area, observation, hypothesis, proposed_change, evidence_gate) -> dict:
    return {"priority": priority, "area": area, "observation": observation,
            "hypothesis": hypothesis, "proposed_change": proposed_change,
            "evidence_gate": evidence_gate, "paper_only": True, "auto_apply": False}


def _rank(proposals: list) -> list:
    order = {P_HIGH: 0, P_MED: 1, P_LOW: 2}
    return sorted(proposals, key=lambda p: order.get(p["priority"], 3))


def synthesize(report: dict, *, min_samples: int = 50) -> dict:
    """Inspect the report and return ranked next-experiment proposals + a plain-English summary."""
    report = report or {}
    proposals: list = []

    # --- 1) Signal-edge: a confidently anti-predictive signal is a FADE opportunity ------------- #
    se = _deep_get(report, "signal_edge") or {}
    for fc in (se.get("fade_candidates") or []):
        if int(fc.get("n", 0) or 0) >= min_samples:
            proposals.append(_proposal(
                P_HIGH, "signals",
                "Signal '%s' (%s) is anti-predictive: acc %.3f over n=%d, Wilson upper %.3f < 0.5."
                % (fc.get("source"), fc.get("context"), float(fc.get("accuracy") or 0),
                   int(fc.get("n") or 0), float(fc.get("wilson_hi") or 0)),
                "Trading the INVERSE of this signal has positive expected accuracy.",
                "Promote source=%s to FADE in the signal-edge layer (trade inverse), gated + capped."
                % fc.get("source"),
                "FADE only while Wilson upper stays < 0.5 on a rolling window; demote if it crosses."))
    for fl in (se.get("follow_candidates") or []):
        if int(fl.get("n", 0) or 0) >= min_samples:
            proposals.append(_proposal(
                P_MED, "signals",
                "Signal '%s' (%s) is reliably right: Wilson lower %.3f > 0.5 over n=%d."
                % (fl.get("source"), fl.get("context"), float(fl.get("wilson_lo") or 0),
                   int(fl.get("n") or 0)),
                "Following this signal in-context adds directional edge.",
                "Promote source=%s/%s to FOLLOW, small size, gated." % (fl.get("source"), fl.get("context")),
                "Keep FOLLOW only while Wilson lower > breakeven; walk-forward must hold."))

    # --- 2) Verifier: is the maker-checker's veto earning its keep? ----------------------------- #
    vq = _deep_get(report, "veto_quality") or {}
    if vq.get("verdict") == "vetoes_costing_edge":
        proposals.append(_proposal(
            P_HIGH, "verifier",
            "Verifier veto_quality=vetoes_costing_edge: %d vetoed setups would have won at "
            "win-rate %.3f (pnl %.2f)." % (int(vq.get("n") or 0),
                                           float(vq.get("vetoed_would_have_win_rate") or 0),
                                           float(vq.get("vetoed_would_have_pnl_usd") or 0)),
            "The 'when unsure, veto' verifier is destroying real edge, not protecting capital.",
            "Wire explore_approve into the follow path (shrink instead of hard-veto) and/or soften "
            "the verifier prompt; re-grade.",
            "Only while veto_quality stays 'vetoes_costing_edge' at n>=min; revert if it flips."))
    elif vq.get("verdict") == "good_vetoes":
        proposals.append(_proposal(
            P_LOW, "verifier",
            "Verifier veto_quality=good_vetoes: the vetoed setups would have lost — the veto helps.",
            "Keep the verifier strict; do NOT wire explore_approve yet.",
            "No change.", "Re-check each soak; act only if it flips to vetoes_costing_edge."))

    # --- 3) Dependency-arb: scale the measured edge once it's real ------------------------------ #
    dep_out = _deep_get(report, "outcome") or {}
    cal = dep_out.get("calibration_by_entry_bucket") or _deep_get(report, "buckets") or {}
    for bucket, st in (cal.items() if isinstance(cal, dict) else []):
        st = st or {}
        n = int(st.get("n", 0) or 0)
        wr = st.get("win_rate")
        pf = st.get("profit_factor")
        if n >= 20 and wr is not None and float(wr) >= 0.55 and (pf is None or float(pf) >= 1.0):
            proposals.append(_proposal(
                P_MED, "dependency_arb",
                "Dep-arb entry-bucket %s is outcome-proven: win_rate %.3f over n=%d (PF %s)."
                % (bucket, float(wr), n, pf),
                "This bucket has real, settled edge that flat $50 sizing under-exploits.",
                "Enable Kelly sizing (Lever C) for this bucket once walk-forward passes.",
                "Walk-forward holdout PF >= 1.0 and n_holdout >= 5 before size > flat."))

    # --- 4) Risk-free arb: report whether the capture change is firing -------------------------- #
    arb = _deep_get(report, "arbitrage") or {}
    if isinstance(arb, dict) and int(arb.get("scans", 0) or 0) > 0:
        executed = int(arb.get("executed", 0) or 0)
        nm = int(arb.get("near_miss_within_eps", 0) or 0)
        rejb = arb.get("arb_rejected_by_reason") or {}
        nonatomic_rejects = sum(v for k, v in rejb.items() if str(k).startswith("nonatomic"))
        if executed == 0 and nonatomic_rejects == 0 and nm > 0:
            proposals.append(_proposal(
                P_LOW, "arbitrage",
                "Risk-free arb still 0 executed with %d near-misses and no nonatomic_* rejects — the "
                "non-atomic cost filter may not be active." % nm,
                "Either the WS4 env (nonatomic on, eps 0.003) hasn't deployed, or books are genuinely "
                "too efficient for a true dutch book.",
                "Verify PULSE_ARB_NONATOMIC_ENABLED=1 and epsilon on the running VPS.",
                "Expect occasional captures with nonatomic_* rejects once deployed; else it's market "
                "efficiency, not a bug."))

    # --- 5) Directional funnel: is the WS2 un-pause actually collecting data? ------------------- #
    lifecycle = _deep_get(report, "candidate_lifecycle") or {}
    terminals = (lifecycle.get("terminals") or {}) if isinstance(lifecycle, dict) else {}
    accepted = int(terminals.get("accepted", 0) or 0)
    created = int(lifecycle.get("created", 0) or 0) if isinstance(lifecycle, dict) else 0
    if created > 100 and accepted == 0:
        proposals.append(_proposal(
            P_HIGH, "directional",
            "Lifecycle: %d candidates created, 0 accepted — directional is still collecting no data."
            % created,
            "A gate downstream of the WS2 exploration (verifier veto / underdog floor / down-bias) is "
            "still blocking every candidate.",
            "Check rejected_by_stage; if execution-gate/verifier dominate, wire explore_approve or "
            "relax the underdog floor quota for exploration.",
            "Need accepted>0 and settled>0 before any bucket can be judged."))

    # --- 6) 5x headline ------------------------------------------------------------------------- #
    fx = _deep_get(report, "five_x_improvement_status")
    ratio = _deep_get(report, "improvement_ratio")
    if fx and fx != "proven" and ratio is not None:
        primary = _deep_get(report, "primary_edge_source")
        proposals.append(_proposal(
            P_MED, "headline",
            "5x not proven (improvement_ratio %.3f); primary edge source: %s." % (float(ratio), primary),
            "Total P&L is below the 5x baseline; the proven lane should get the capital.",
            "Concentrate sizing/iteration on the primary edge source (%s) and park unproven lanes."
            % primary,
            "improvement_ratio must trend up across soaks with the proven lane leading."))

    # --- 7) Dep-arb experiments: mid-convergence, capture bleed, conjunction vs nested ----------- #
    dep = _deep_get(report, "dependency_arbitrage") or {}
    if isinstance(dep, dict) and dep.get("enabled") is not False:
        exp = dep.get("experiments") or {}
        booking = dep.get("booking") or {}
        settled_n = int(booking.get("settled_n") or dep.get("settled") or 0)
        capture = booking.get("capture_ratio")
        theoretical = float(booking.get("theoretical_settled_usd") or 0)
        if settled_n >= 3 and capture is not None and float(capture) < 0.10 and theoretical > 50:
            proposals.append(_proposal(
                P_HIGH, "dependency_arb_experiments",
                "Dep-arb capture_ratio %.3f on $%.0f theoretical (%d settled) — edge bleeds at hold."
                % (float(capture), theoretical, settled_n),
                "nested_implication holds to resolution; mid-gap may converge before settlement.",
                "Keep nested_execute=0; soak mid_convergence observer; if 60s converged_rate>0.5, "
                "prototype mid-exit paper lane.",
                "Mid-convergence n>=10 at 60s with converged_rate>=0.5 before mid-exit execute."))

        mid = exp.get("mid_convergence") or {}
        by_h = mid.get("by_horizon") or {}
        h60 = by_h.get("60") or {}
        n60 = int(h60.get("n") or 0)
        rate60 = h60.get("converged_rate")
        if n60 >= 10 and rate60 is not None:
            if float(rate60) >= 0.50:
                proposals.append(_proposal(
                    P_HIGH, "dependency_arb_experiments",
                    "Mid-gap converges within 60s on %.1f%% of %d observations (rate=%.3f)."
                    % (float(rate60) * 100, n60, float(rate60)),
                    "Violation gaps mean-revert quickly — hold-to-resolution leaves money on table.",
                    "Design paper mid-exit at 60s when gap_decay>50%%; size only conjunction binds.",
                    "Walk-forward on mid-exit paper fills: PF>=1.0 and n>=20 before sizing up."))
            elif float(rate60) < 0.30:
                proposals.append(_proposal(
                    P_MED, "dependency_arb_experiments",
                    "Mid-gap rarely converges by 60s (rate=%.3f, n=%d) — heuristic gap may be noise."
                    % (float(rate60), n60),
                    "Child/parent mid divergence may not mean-revert on this horizon.",
                    "Stay conjunction-only execute; treat nested_implication as observe-only forever.",
                    "converged_rate stays <0.30 across two soaks with n60>=20."))

        if exp.get("nested_execute_enabled"):
            cal = dep.get("dependency_arb_calibration") or {}
            for bucket, st in (cal.get("by_entry_bucket") or {}).items():
                st = st or {}
                n = int(st.get("n") or 0)
                pf = st.get("profit_factor")
                if n >= 5 and pf is not None and float(pf) < 1.0:
                    proposals.append(_proposal(
                        P_HIGH, "dependency_arb_experiments",
                        "nested_execute still ON but bucket %s bleeds (PF=%.2f, n=%d)."
                        % (bucket, float(pf), n),
                        "Heuristic nested_implication is actively losing settled paper P&L.",
                        "Set PULSE_DEPENDENCY_ARB_NESTED_EXECUTE=0 (conjunction-only).",
                        "Auto-apply should flip nested_execute off; verify in experiments block."))
                    break

        last_v = dep.get("last_violations") or []
        conj_seen = sum(1 for v in last_v
                        if str((v or {}).get("constraint_type", "")) == "conjunction_implication")
        nested_seen = sum(1 for v in last_v
                          if str((v or {}).get("constraint_type", "")) == "nested_implication")
        executed = int(dep.get("executed") or 0)
        if conj_seen > 0 and executed == 0 and not exp.get("nested_execute_enabled"):
            proposals.append(_proposal(
                P_MED, "dependency_arb_experiments",
                "Conjunction violations seen (%d recent) but 0 dep-arb fills — true arb not binding."
                % conj_seen,
                "Clock-skew or walk-forward may block conjunction; nested is already off.",
                "Verify PULSE_DEPENDENCY_ARB_CONJUNCTION=1; review rejected_by_reason for "
                "clock_skew_* and walk_forward.",
                "At least 1 conjunction paper fill OR explicit gate reason dominates rejects."))
        elif nested_seen > 5 and conj_seen == 0:
            proposals.append(_proposal(
                P_LOW, "dependency_arb_experiments",
                "Only nested_implication violations (%d recent), no conjunction binds."
                % nested_seen,
                "TRUE multi-child Fréchet floor rarely fires on current BTC books.",
                "Keep conjunction=1 for measurement; nested observe-only via nested_execute=0.",
                "conjunction_implication appears in last_violations at least once per soak."))

    ranked = _rank(proposals)
    return {
        "schema": "loop_synthesis/1.0", "observe_only": True, "auto_apply": False,
        "proposal_count": len(ranked),
        "top_priority": (ranked[0]["area"] if ranked else None),
        "proposals": ranked,
        "summary": _summary(ranked),
        "note": ("Advisory next-experiment proposals from live performance. Paper-only; never edits "
                 "config or trades. Each names the evidence gate that would justify acting."),
    }


def _summary(ranked: list) -> str:
    if not ranked:
        return "No actionable experiment surfaced from the current report — keep soaking for samples."
    highs = [p for p in ranked if p["priority"] == P_HIGH]
    lead = ranked[0]
    head = "%d proposal(s); %d high-priority." % (len(ranked), len(highs))
    return "%s Top: [%s] %s" % (head, lead["area"], lead["proposed_change"])
