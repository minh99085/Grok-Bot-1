"""Claude maker-checker for dependency-arbitrage (conjunction binds only).

Independent of the directional verifier. Reviews proposed parent-UP paper fills on validated
conjunction_implication violations. Can ONLY veto or shrink — never authorize or enlarge.
PAPER ONLY.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from typing import Callable, Optional

from engine.pulse.grok_intel import _parse_json, GrokBudget
from engine.pulse.claude_client import claude_chat
from engine.pulse.verifier import normalize_verdict


def build_dep_arb_verify_payload(
    violation,
    trade: dict,
    *,
    bregman_diag: Optional[dict] = None,
    experiments: Optional[dict] = None,
    calibration_bucket: Optional[dict] = None,
    parent_book_age_s: Optional[float] = None,
    child_book_age_s: Optional[float] = None,
    grok_dependency: Optional[dict] = None,
    grok_convergence: Optional[dict] = None,
) -> dict:
    """Compact context for the dep-arb verifier (no maker reasoning)."""
    vdict = violation.to_dict() if hasattr(violation, "to_dict") else dict(violation or {})
    return {
        "lane": "dependency_arbitrage",
        "paper_only": True,
        "constraint_type": vdict.get("constraint_type"),
        "violation": vdict,
        "trade_preview": {
            "entry_vwap": trade.get("entry_vwap"),
            "cost_usd": trade.get("cost_usd"),
            "shares": trade.get("shares"),
            "expected_profit_usd": trade.get("expected_profit_usd"),
            "violation_magnitude": trade.get("violation_magnitude"),
            "implied_bound": trade.get("implied_bound"),
        },
        "bregman": bregman_diag or {},
        "experiments": experiments or {},
        "calibration_bucket": calibration_bucket or {},
        "book_ages_s": {
            "parent": parent_book_age_s,
            "child": child_book_age_s,
        },
        "grok_dependency": grok_dependency or {},
        "grok_convergence_prior": grok_convergence or {},
    }


def shrink_dep_arb_trade(trade: dict, max_size_fraction: float) -> dict:
    """Scale a paper dep-arb trade down (never up)."""
    frac = max(0.0, min(1.0, float(max_size_fraction)))
    if frac >= 1.0 - 1e-9:
        return trade
    out = dict(trade)
    for key in ("cost_usd", "shares", "trade_usd", "expected_profit_usd",
                "theoretical_profit_usd", "heuristic_profit_usd", "booked_profit_usd"):
        if key in out and out[key] is not None:
            out[key] = round(float(out[key]) * frac, 6)
    out["verifier_size_fraction"] = round(frac, 4)
    return out


def make_dep_arb_verifier_fn(*, model: Optional[str] = None, timeout_s: float = 20.0,
                             chat=claude_chat):
    box: dict = {}
    system = (
        "You are an INDEPENDENT risk verifier (maker-checker) for PAPER BTC dependency-arbitrage. "
        "A deterministic LCMM scanner proposed a parent-UP fill on a conjunction_implication bind "
        "(TRUE logic: all nested shorter windows UP implies the longer parent UP, Fréchet floor). "
        "You did NOT see the scanner's full reasoning. VETO when: entry_vwap is high (>0.52) with "
        "poor bucket calibration (low PF / bleeding), mid_convergence data suggests hold-to-resolution "
        "loses despite a gap, bregman projection is weak, books are asymmetrically stale, or the "
        "bind looks like noise not arb. APPROVE only when the conjunction floor is materially violated "
        "and capture (mid-exit or resolution) is plausible. You can ONLY veto or shrink "
        "max_size_fraction — never enlarge or force a trade. When unsure, veto."
    )

    def _verify(payload: dict) -> Optional[dict]:
        prompt = (
            "Review this proposed PAPER dependency-arb parent-UP fill. Respond STRICT JSON ONLY: "
            "{\"approve\":true|false,\"max_size_fraction\":<0-1>,\"confidence\":<0-1>,"
            "\"reason\":\"<short>\"}.\nCONTEXT: "
            + json.dumps(payload, default=str)[:8000]
        )
        return normalize_verdict(
            _parse_json(chat(prompt, model=model, timeout_s=timeout_s, box=box,
                             system=system, max_tokens=512)))
    return _verify


class ClaudeDepArbVerifier:
    """Background Claude worker for conjunction-only dep-arb maker-checker."""

    def __init__(
        self,
        *,
        verify_fn=None,
        budget: Optional[GrokBudget] = None,
        enabled: bool = True,
        fail_open: bool = True,
        require_verdict: bool = False,
        conjunction_only: bool = True,
        max_pending: int = 100,
        max_results: int = 2000,
        veto_quality_min_n: int = 10,
    ):
        self._fn = verify_fn if verify_fn is not None else make_dep_arb_verifier_fn()
        self._budget = budget
        self.enabled = bool(enabled)
        self.fail_open = bool(fail_open)
        self.require_verdict = bool(require_verdict)
        self.conjunction_only = bool(conjunction_only)
        self.veto_quality_min_n = int(veto_quality_min_n)
        self._lock = threading.Lock()
        self._queue: deque = deque(maxlen=int(max_pending))
        self._results: dict = {}
        self._order: deque = deque(maxlen=int(max_results))
        self._seen: set = set()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.requested = 0
        self.verified = 0
        self.approvals = 0
        self.vetoes = 0
        self.errors = 0
        self.skipped_budget = 0
        self.latency_sum = 0.0
        self.approved_settled = {"n": 0, "wins": 0, "pnl": 0.0}
        self.vetoed_would_have = {"n": 0, "wins": 0, "pnl": 0.0}
        self._graded: set = set()

    def should_verify(self, constraint_type: str) -> bool:
        if not self.enabled:
            return False
        ctype = str(constraint_type or "")
        if self.conjunction_only and ctype != "conjunction_implication":
            return False
        return True

    def decision_id(self, violation, *, child_key: str) -> str:
        pk = str(getattr(violation, "parent_window_key", "") or "")
        ctype = str(getattr(violation, "constraint_type", "") or "")
        return "dep_arb:%s:%s:%s" % (pk, child_key, ctype)

    def request(self, decision_id: str, payload: dict) -> None:
        if not decision_id or not self.enabled:
            return
        with self._lock:
            if decision_id in self._seen:
                return
            self._seen.add(decision_id)
            self._queue.append((decision_id, payload))
            self.requested += 1

    def get(self, decision_id: str) -> Optional[dict]:
        with self._lock:
            r = self._results.get(decision_id)
            return dict(r) if r else None

    def verdict_or_failopen(self, decision_id: str) -> dict:
        v = self.get(decision_id)
        if v is not None:
            return v
        if self.require_verdict:
            return {"approve": False, "max_size_fraction": 0.0, "confidence": 0.0,
                    "reason": "dep_arb_verifier_pending", "pending": True}
        return {
            "approve": bool(self.fail_open),
            "max_size_fraction": 1.0,
            "confidence": 0.0,
            "reason": ("fail_open_no_verdict" if self.fail_open else "fail_closed_no_verdict"),
            "pending": True,
        }

    def _process_one(self) -> bool:
        with self._lock:
            if not self._queue:
                return False
            decision_id, payload = self._queue.popleft()
        if self._budget is not None and not self._budget.try_spend("verifier_dep_arb"):
            with self._lock:
                self.skipped_budget += 1
            return True
        t0 = time.time()
        verdict = None
        try:
            verdict = self._fn(payload)
        except Exception:  # noqa: BLE001
            verdict = None
        with self._lock:
            if verdict is None:
                self.errors += 1
            else:
                verdict["ts"] = time.time()
                verdict["latency_s"] = round(time.time() - t0, 3)
                self.verified += 1
                self.latency_sum += (time.time() - t0)
                self.approvals += int(bool(verdict.get("approve")))
                self.vetoes += int(not verdict.get("approve"))
                self._results[decision_id] = verdict
                self._order.append(decision_id)
                if len(self._results) > self._order.maxlen:
                    self._results.pop(self._order.popleft(), None)
        return True

    def grade(self, decision_id: str, *, won: bool, pnl: float, acted: bool) -> None:
        with self._lock:
            if not decision_id or decision_id in self._graded:
                return
            v = self._results.get(decision_id)
            if not v:
                return
            if v.get("approve") and acted:
                bucket = self.approved_settled
            elif not v.get("approve"):
                bucket = self.vetoed_would_have
            else:
                return
            self._graded.add(decision_id)
            bucket["n"] += 1
            bucket["wins"] += int(bool(won))
            bucket["pnl"] = round(bucket["pnl"] + float(pnl or 0.0), 6)

    def _worker(self) -> None:
        while not self._stop.is_set():
            worked = False
            try:
                worked = self._process_one()
            except Exception:  # noqa: BLE001
                pass
            self._stop.wait(0.2 if worked else 1.0)

    def start(self) -> "ClaudeDepArbVerifier":
        if self.enabled and (self._thread is None or not self._thread.is_alive()):
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._worker, name="claude-dep-arb-verifier", daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def report(self) -> dict:
        with self._lock:
            avg_lat = round(self.latency_sum / self.verified, 3) if self.verified else None
            vwh = self.vetoed_would_have
            veto_quality = {
                "verdict": "insufficient_evidence",
                "n": vwh["n"],
                "vetoed_would_have_win_rate": (
                    round(vwh["wins"] / vwh["n"], 4) if vwh["n"] else None),
                "vetoed_would_have_pnl_usd": round(vwh["pnl"], 4),
                "min_samples": self.veto_quality_min_n,
            }
            if vwh["n"] >= self.veto_quality_min_n:
                if vwh["pnl"] > 0 or (vwh["n"] and (vwh["wins"] / vwh["n"]) > 0.5):
                    veto_quality["verdict"] = "vetoes_costing_edge"
                else:
                    veto_quality["verdict"] = "good_vetoes"
            return {
                "enabled": self.enabled,
                "model": "claude",
                "maker_checker": True,
                "lane": "dependency_arbitrage",
                "conjunction_only": self.conjunction_only,
                "require_verdict": self.require_verdict,
                "fail_open": self.fail_open,
                "veto_quality": veto_quality,
                "requested": self.requested,
                "verified": self.verified,
                "approvals": self.approvals,
                "vetoes": self.vetoes,
                "errors": self.errors,
                "skipped_budget": self.skipped_budget,
                "avg_latency_s": avg_lat,
                "approved_settled": {
                    "n": self.approved_settled["n"],
                    "win_rate": (round(self.approved_settled["wins"] / self.approved_settled["n"], 4)
                                 if self.approved_settled["n"] else None),
                    "pnl_usd": round(self.approved_settled["pnl"], 4),
                },
                "note": ("Independent Claude verifier for conjunction_implication dep-arb fills only. "
                         "Veto or shrink only; never enlarges."),
            }

    def to_state(self) -> dict:
        with self._lock:
            return {
                "requested": self.requested,
                "verified": self.verified,
                "approvals": self.approvals,
                "vetoes": self.vetoes,
                "errors": self.errors,
                "skipped_budget": self.skipped_budget,
                "approved_settled": dict(self.approved_settled),
                "vetoed_would_have": dict(self.vetoed_would_have),
                "results": {k: self._results[k] for k in list(self._order)[-200:]},
            }

    def load_state(self, data: dict) -> None:
        if not data:
            return
        self.requested = int(data.get("requested") or 0)
        self.verified = int(data.get("verified") or 0)
        self.approvals = int(data.get("approvals") or 0)
        self.vetoes = int(data.get("vetoes") or 0)
        self.errors = int(data.get("errors") or 0)
        self.skipped_budget = int(data.get("skipped_budget") or 0)
        self.approved_settled = dict(data.get("approved_settled") or self.approved_settled)
        self.vetoed_would_have = dict(data.get("vetoed_would_have") or self.vetoed_would_have)
        for k, v in (data.get("results") or {}).items():
            self._results[k] = v
            self._seen.add(k)