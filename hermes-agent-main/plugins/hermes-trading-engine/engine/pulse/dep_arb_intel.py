"""Dep-arb intel report block — Grok proposals, convergence prior, Claude verifier (PAPER ONLY).

Structured for overnight soak readability: one headline + four keyed subsections.
"""

from __future__ import annotations

from typing import Optional


def _compact_accepted(accepted: list, *, limit: int = 4) -> list[dict]:
    out = []
    for row in (accepted or [])[-limit:]:
        if not isinstance(row, dict):
            continue
        out.append({
            "constraint_type": row.get("constraint_type"),
            "parent_window_key": row.get("parent_window_key"),
            "child_window_keys": row.get("child_window_keys"),
            "violation_magnitude": row.get("violation_magnitude"),
            "parent_up_mid": row.get("parent_up_mid"),
        })
    return out


def _veto_quality_block(verifier: Optional[dict]) -> dict:
    verifier = verifier or {}
    vq = dict(verifier.get("veto_quality") or {})
    verdict = str(vq.get("verdict") or "insufficient_evidence")
    n = int(vq.get("n") or 0)
    wr = vq.get("vetoed_would_have_win_rate")
    pnl = vq.get("vetoed_would_have_pnl_usd")
    min_n = int(vq.get("min_samples") or 10)
    parts = ["verdict=%s" % verdict, "n=%d" % n]
    if wr is not None:
        parts.append("vetoed-would-win=%.2f" % float(wr))
    if pnl is not None:
        parts.append("vetoed-would-pnl=$%.2f" % float(pnl))
    return {
        "verdict": verdict,
        "n": n,
        "min_samples": min_n,
        "vetoed_would_have_win_rate": wr,
        "vetoed_would_have_pnl_usd": pnl,
        "headline": " | ".join(parts),
        "ready_for_gate": bool(n >= min_n and verdict != "insufficient_evidence"),
    }


def _grok_proposals_block(
    grok_dependency: Optional[dict],
    grok_screener: Optional[dict],
) -> dict:
    grok_dependency = grok_dependency or {}
    grok_screener = grok_screener or {}
    proposals_in = int(grok_dependency.get("dependency_proposals") or 0)
    validated = int(grok_dependency.get("deterministic_validated_dependencies") or 0)
    rejected_n = len(grok_dependency.get("rejected_dependencies") or [])
    enabled = bool(grok_screener.get("enabled")) or proposals_in > 0
    parts = ["in=%d" % proposals_in, "validated=%d" % validated]
    if rejected_n:
        parts.append("rejected=%d" % rejected_n)
    return {
        "enabled": enabled,
        "observe_only": True,
        "proposals_in": proposals_in,
        "validated": validated,
        "rejected": rejected_n,
        "accepted_recent": _compact_accepted(grok_dependency.get("accepted_dependencies") or []),
        "screener": {
            "calls": grok_screener.get("calls"),
            "errors": grok_screener.get("errors"),
            "skipped_budget": grok_screener.get("skipped_budget"),
            "proposals_cached": grok_screener.get("proposals_cached"),
            "age_s": grok_screener.get("age_s"),
            "interval_s": grok_screener.get("interval_s"),
        } if grok_screener else {"enabled": False},
        "headline": "Grok proposals: " + ", ".join(parts),
    }


def _grok_convergence_block(grok_convergence: Optional[dict]) -> dict:
    grok_convergence = grok_convergence or {}
    enabled = bool(grok_convergence.get("enabled"))
    acc = grok_convergence.get("accuracy_60s")
    scored = int(grok_convergence.get("scored_60s") or 0)
    if not enabled:
        return {"enabled": False, "observe_only": True, "headline": "Grok 60s prior: off"}
    if scored <= 0:
        headline = "Grok 60s prior: no grades yet (requested=%s)" % (
            grok_convergence.get("requested"))
    else:
        headline = "Grok 60s prior: acc=%s n=%d" % (acc, scored)
    return {
        "enabled": True,
        "observe_only": True,
        "horizon_s": grok_convergence.get("horizon_s", 60),
        "accuracy_60s": acc,
        "scored_60s": scored,
        "requested": grok_convergence.get("requested"),
        "predicted": grok_convergence.get("predicted"),
        "errors": grok_convergence.get("errors"),
        "skipped_budget": grok_convergence.get("skipped_budget"),
        "cached": grok_convergence.get("cached"),
        "headline": headline,
    }


def _claude_verifier_block(claude_verifier: Optional[dict]) -> dict:
    claude_verifier = claude_verifier or {}
    enabled = bool(claude_verifier.get("enabled"))
    if not enabled:
        return {"enabled": False, "headline": "Claude dep-arb verifier: off"}
    approved = claude_verifier.get("approved_settled") or {}
    an = int(approved.get("n") or 0)
    parts = [
        "verified=%s" % claude_verifier.get("verified"),
        "approve=%s" % claude_verifier.get("approvals"),
        "veto=%s" % claude_verifier.get("vetoes"),
    ]
    if an:
        parts.append("settled_n=%d wr=%s" % (an, approved.get("win_rate")))
    return {
        "enabled": True,
        "conjunction_only": claude_verifier.get("conjunction_only"),
        "fail_open": claude_verifier.get("fail_open"),
        "require_verdict": claude_verifier.get("require_verdict"),
        "verified": claude_verifier.get("verified"),
        "approvals": claude_verifier.get("approvals"),
        "vetoes": claude_verifier.get("vetoes"),
        "errors": claude_verifier.get("errors"),
        "skipped_budget": claude_verifier.get("skipped_budget"),
        "avg_latency_s": claude_verifier.get("avg_latency_s"),
        "approved_settled": approved,
        "headline": "Claude verifier: " + ", ".join(str(x) for x in parts),
    }


def build_dep_arb_intel_report(
    *,
    grok_dependency: Optional[dict] = None,
    grok_screener: Optional[dict] = None,
    grok_convergence: Optional[dict] = None,
    claude_verifier: Optional[dict] = None,
) -> dict:
    """Operator-facing dep-arb intel slice for light/full reports and overnight soaks."""
    grok_proposals = _grok_proposals_block(grok_dependency, grok_screener)
    grok_conv = _grok_convergence_block(grok_convergence)
    claude = _claude_verifier_block(claude_verifier)
    veto_quality = _veto_quality_block(claude_verifier)

    any_on = (
        grok_proposals.get("enabled")
        or grok_conv.get("enabled")
        or claude.get("enabled")
    )
    headline_parts = [
        grok_proposals.get("headline", ""),
        grok_conv.get("headline", ""),
        claude.get("headline", ""),
        veto_quality.get("headline", ""),
    ]
    return {
        "enabled": bool(any_on),
        "observe_only": True,
        "affects_trading": False,
        "headline": " · ".join(p for p in headline_parts if p),
        "grok_proposals": grok_proposals,
        "grok_convergence": grok_conv,
        "claude_verifier": claude,
        "veto_quality": veto_quality,
        "note": ("Tier-1 dep-arb intel: Grok constraint screen + 60s convergence prior (observe); "
                 "Claude maker-checker on conjunction binds only. veto_quality grades at settle."),
    }