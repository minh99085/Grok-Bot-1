"""Grok advisory 60s mid-gap convergence prior for dependency-arbitrage (OBSERVE + optional gate).

Given a validated LCMM violation snapshot, Grok estimates whether the parent/child UP mid-gap will
mean-revert within 60s (vs bleeding if held to resolution). Advisory only by default — feeds Claude
verifier payload and reports; optional low-prior gate when enabled. PAPER ONLY.
"""

from __future__ import annotations

import json
import re
import threading
import time
from collections import deque
from typing import Optional

from engine.pulse.grok_intel import _parse_json, _grok_chat

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}")


def neutral_prior(*, reason: str = "no_prior") -> dict:
    return {
        "observe_only": True,
        "converge_60s": None,
        "hold_to_resolution_risk": "unknown",
        "reason": reason,
        "pending": True,
    }


def parse_convergence_response(raw: str) -> Optional[dict]:
    """Parse Grok JSON: converge_60s, hold_to_resolution_risk, reason."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = _JSON_BLOCK_RE.search(text)
        if m:
            try:
                data = json.loads(m.group(0))
            except json.JSONDecodeError:
                data = None
    if not isinstance(data, dict):
        return None
    try:
        conv = data.get("converge_60s")
        conv_f = max(0.0, min(1.0, float(conv))) if conv is not None else None
    except (TypeError, ValueError):
        conv_f = None
    risk = str(data.get("hold_to_resolution_risk") or "unknown").strip().lower()
    if risk not in ("low", "med", "medium", "high", "unknown"):
        risk = "unknown"
    if risk == "medium":
        risk = "med"
    return {
        "observe_only": True,
        "converge_60s": round(conv_f, 4) if conv_f is not None else None,
        "hold_to_resolution_risk": risk,
        "reason": str(data.get("reason") or "")[:400],
        "pending": False,
    }


GROK_CONVERGENCE_PROMPT = """You are a Polymarket microstructure analyst (ADVISORY ONLY).
Given a dependency-arbitrage violation snapshot (parent/child UP mids, gap, book ages), estimate
whether the mid-gap will MEAN-REVERT within 60 seconds (child UP mid falling toward parent UP mid)
vs staying wide until window resolution (hold-to-resolution risk).

Respond STRICT JSON ONLY:
{"converge_60s": <0.0-1.0 probability gap shrinks >50% within 60s>,
 "hold_to_resolution_risk": "low|med|high",
 "reason": "<one sentence>"}

Be skeptical: most nested gaps on efficient BTC books do NOT converge. Use book staleness asymmetry
and gap magnitude. Do NOT recommend trades."""


def build_convergence_context(
    violation,
    parent,
    child,
    *,
    now: float,
    parent_book_age_s: Optional[float] = None,
    child_book_age_s: Optional[float] = None,
    mid_convergence_empirical: Optional[dict] = None,
) -> dict:
    """Context dict for Grok convergence prior (and prompt builder)."""
    from engine.pulse.dependency_arb import _up_mid

    p_mid = getattr(violation, "parent_up_mid", None) or _up_mid(parent)
    c_mid = (getattr(violation, "child_up_mids", None) or [None])[0]
    if c_mid is None:
        c_mid = _up_mid(child)
    gap = None
    if p_mid is not None and c_mid is not None:
        gap = round(float(c_mid) - float(p_mid), 6)
    return {
        "constraint_type": str(getattr(violation, "constraint_type", "") or ""),
        "parent_window_key": str(getattr(violation, "parent_window_key", "") or ""),
        "child_window_keys": list(getattr(violation, "child_window_keys", None) or []),
        "parent_up_mid": p_mid,
        "child_up_mid": c_mid,
        "gap": gap,
        "violation_magnitude": getattr(violation, "violation_magnitude", None),
        "implied_bound": getattr(violation, "implied_bound", None),
        "parent_book_age_s": parent_book_age_s,
        "child_book_age_s": child_book_age_s,
        "parent_seconds_to_close": (
            max(0.0, float(getattr(parent, "close_ts", 0) or 0) - float(now))
            if parent is not None else None),
        "empirical_mid_convergence": mid_convergence_empirical or {},
        "ts": float(now),
    }


def build_convergence_prompt(context: dict) -> str:
    return GROK_CONVERGENCE_PROMPT + "\n\nSnapshot:\n" + json.dumps(context, default=str, indent=1)


def violation_prior_key(violation) -> str:
    pk = str(getattr(violation, "parent_window_key", "") or "")
    ck = str((getattr(violation, "child_window_keys", None) or [""])[0] or "")
    ctype = str(getattr(violation, "constraint_type", "") or "")
    return "grok_conv:%s:%s:%s" % (pk, ck, ctype)


def make_convergence_fn(*, model: str = "grok-4.3", timeout_s: float = 15.0):
    box: dict = {}

    def _predict(context: dict) -> Optional[dict]:
        prompt = build_convergence_prompt(context)
        raw = _grok_chat(prompt, model=model, timeout_s=timeout_s, box=box)
        return parse_convergence_response(raw) if raw else None

    return _predict


def convergence_prior_passes_gate(
    prior: dict,
    *,
    min_converge_60s: float = 0.35,
    max_hold_risk: str = "high",
) -> tuple[bool, str]:
    """Optional advisory gate: False when Grok prior is strongly anti-convergence."""
    if not prior or prior.get("pending"):
        return True, "no_prior_fail_open"
    conv = prior.get("converge_60s")
    risk = str(prior.get("hold_to_resolution_risk") or "unknown").lower()
    if conv is not None and float(conv) < float(min_converge_60s):
        return False, "grok_convergence_low_60s=%.3f" % float(conv)
    if risk == max_hold_risk:
        return False, "grok_hold_risk_high"
    return True, "ok"


class GrokDepConvergencePrior:
    """Background Grok worker: per-violation 60s convergence prior (cached, graded vs observer)."""

    def __init__(
        self,
        *,
        predict_fn=None,
        budget=None,
        max_pending: int = 80,
        max_results: int = 500,
        max_age_s: float = 120.0,
    ):
        self._fn = predict_fn if predict_fn is not None else make_convergence_fn()
        self._budget = budget
        self.max_age_s = float(max_age_s)
        self._lock = threading.Lock()
        self._queue: deque = deque(maxlen=int(max_pending))
        self._results: dict = {}
        self._order: deque = deque(maxlen=int(max_results))
        self._seen: set = set()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.requested = 0
        self.predicted = 0
        self.errors = 0
        self.skipped_budget = 0
        self.scored = 0
        self.correct_60s = 0

    def request(self, key: str, context: dict) -> None:
        if not key:
            return
        with self._lock:
            existing = self._results.get(key)
            if existing and not existing.get("pending"):
                age = float(time.time()) - float(existing.get("ts") or 0)
                if age < self.max_age_s:
                    return
            if key in self._seen and key in self._results:
                return
            self._seen.add(key)
            self._results[key] = {**neutral_prior(reason="pending"), "ts": time.time()}
            self._queue.append((key, dict(context)))
            self.requested += 1

    def get(self, key: str) -> dict:
        with self._lock:
            r = self._results.get(key)
            if not r:
                return neutral_prior(reason="not_requested")
            age = float(time.time()) - float(r.get("ts") or 0)
            if age > self.max_age_s and not r.get("pending"):
                return neutral_prior(reason="stale_prior")
            return dict(r)

    def grade(self, key: str, *, converged_60s: bool) -> None:
        """Grade prior vs empirical observer outcome at 60s horizon."""
        with self._lock:
            r = self._results.get(key)
            if not r or r.get("pending"):
                return
            conv = r.get("converge_60s")
            if conv is None:
                return
            self.scored += 1
            predicted_yes = float(conv) >= 0.5
            if predicted_yes == bool(converged_60s):
                self.correct_60s += 1

    def _process_one(self) -> bool:
        with self._lock:
            if not self._queue:
                return False
            key, context = self._queue.popleft()
        if self._budget is not None and not self._budget.try_spend("dep_convergence"):
            with self._lock:
                self.skipped_budget += 1
            return True
        prior = None
        try:
            prior = self._fn(context)
        except Exception:  # noqa: BLE001
            prior = None
        with self._lock:
            if prior is None:
                self.errors += 1
                self._results[key] = {**neutral_prior(reason="grok_error"), "ts": time.time()}
            else:
                prior["ts"] = time.time()
                self._results[key] = prior
                self._order.append(key)
                self.predicted += 1
                if len(self._results) > self._order.maxlen:
                    old = self._order.popleft()
                    self._results.pop(old, None)
        return True

    def _worker(self) -> None:
        while not self._stop.is_set():
            worked = False
            try:
                worked = self._process_one()
            except Exception:  # noqa: BLE001
                pass
            self._stop.wait(0.15 if worked else 0.8)

    def start(self) -> "GrokDepConvergencePrior":
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._worker, name="grok-dep-convergence", daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def report(self) -> dict:
        with self._lock:
            acc = (round(self.correct_60s / self.scored, 4) if self.scored else None)
            return {
                "enabled": True,
                "observe_only": True,
                "affects_trading": False,
                "horizon_s": 60,
                "requested": self.requested,
                "predicted": self.predicted,
                "errors": self.errors,
                "skipped_budget": self.skipped_budget,
                "scored_60s": self.scored,
                "accuracy_60s": acc,
                "cached": len(self._results),
                "max_age_s": self.max_age_s,
                "note": ("Grok prior: P(gap mean-reverts >50% within 60s). Graded vs mid_observer."),
            }

    def to_state(self) -> dict:
        with self._lock:
            return {
                "requested": self.requested,
                "predicted": self.predicted,
                "errors": self.errors,
                "skipped_budget": self.skipped_budget,
                "scored_60s": self.scored,
                "correct_60s": self.correct_60s,
                "results": {k: self._results[k] for k in list(self._order)[-100:]},
            }

    def load_state(self, data: dict) -> None:
        if not data:
            return
        self.requested = int(data.get("requested") or 0)
        self.predicted = int(data.get("predicted") or 0)
        self.errors = int(data.get("errors") or 0)
        self.skipped_budget = int(data.get("skipped_budget") or 0)
        self.scored = int(data.get("scored_60s") or 0)
        self.correct_60s = int(data.get("correct_60s") or 0)
        for k, v in (data.get("results") or {}).items():
            self._results[k] = v
            self._seen.add(k)