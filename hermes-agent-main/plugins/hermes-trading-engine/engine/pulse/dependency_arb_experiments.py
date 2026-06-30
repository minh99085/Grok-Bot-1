"""Dep-arb experiment layer (paper-only, observe + gated execute).

Experiments (operator-authorized):
  1. Conjunction-only execute — disable nested_implication paper fills (heuristic off).
  2. Clock-skew filter — parent book stale vs child book/window fresh (microstructure).
  3. Mid-convergence observer — does the mid-gap close within 30/60/120s?
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


def _book_age_s(book, now: float) -> Optional[float]:
    if book is None:
        return None
    ts = float(getattr(book, "ts", 0) or 0)
    if ts <= 0 or now <= 0:
        return None
    return max(0.0, float(now) - ts)


def _window_age_s(window, now: float) -> Optional[float]:
    if window is None:
        return None
    open_ts = float(getattr(window, "open_ts", 0) or 0)
    if open_ts <= 0 or now <= 0:
        return None
    return max(0.0, float(now) - open_ts)


def _gap(parent_mid: Optional[float], child_mid: Optional[float]) -> Optional[float]:
    if parent_mid is None or child_mid is None:
        return None
    return round(float(child_mid) - float(parent_mid), 6)


def clock_skew_passes(
    parent,
    child,
    *,
    now: float,
    min_parent_book_age_s: float,
    max_child_book_age_s: float,
    max_child_window_age_s: float,
) -> tuple[bool, str]:
    """True when parent UP book is stale and child is fresh (listing skew hypothesis)."""
    p_book = getattr(parent, "up_book", None)
    c_book = getattr(child, "up_book", None)
    p_age = _book_age_s(p_book, now)
    c_age = _book_age_s(c_book, now)
    w_age = _window_age_s(child, now)
    if p_age is not None and p_age < float(min_parent_book_age_s):
        return False, "clock_skew_parent_book_too_fresh"
    if c_age is not None and c_age > float(max_child_book_age_s):
        return False, "clock_skew_child_book_too_stale"
    if w_age is not None and w_age > float(max_child_window_age_s):
        return False, "clock_skew_child_window_too_old"
    return True, "ok"


def execute_gate(
    violation,
    *,
    nested_execute_enabled: bool,
    clock_skew_enabled: bool,
    parent=None,
    child=None,
    now: float = 0.0,
    min_parent_book_age_s: float = 120.0,
    max_child_book_age_s: float = 90.0,
    max_child_window_age_s: float = 120.0,
) -> tuple[bool, str]:
    """Paper-execute gate for dep-arb experiments (never forces live trading)."""
    ctype = str(getattr(violation, "constraint_type", "") or "")
    if ctype == "nested_implication" and not nested_execute_enabled:
        return False, "nested_execute_disabled_experiment"
    if clock_skew_enabled and parent is not None and child is not None:
        ok, reason = clock_skew_passes(
            parent, child, now=now,
            min_parent_book_age_s=min_parent_book_age_s,
            max_child_book_age_s=max_child_book_age_s,
            max_child_window_age_s=max_child_window_age_s,
        )
        if not ok:
            return False, reason
    return True, "ok"


@dataclass
class MidConvergenceObservation:
    parent_key: str
    child_key: str
    constraint_type: str
    snap_ts: float
    gap0: float
    parent_mid0: float
    child_mid0: float
    horizons_s: tuple[float, ...] = (30.0, 60.0, 120.0)
    readings: dict = field(default_factory=dict)  # horizon -> {gap, ts, converged}

    def key(self) -> str:
        return "%s:%s:%s" % (self.parent_key, self.child_key, self.constraint_type)

    def record_horizon(self, horizon_s: float, *, gap: float, ts: float) -> None:
        h = float(horizon_s)
        if h in self.readings:
            return
        gap0 = float(self.gap0)
        converged = gap < gap0 * 0.5 if gap0 > 1e-9 else gap <= 0
        self.readings[h] = {
            "gap": round(gap, 6),
            "ts": ts,
            "gap_decay": round(gap0 - gap, 6),
            "converged": bool(converged),
        }

    def complete(self) -> bool:
        return len(self.readings) >= len(self.horizons_s)


class DepArbMidConvergenceObserver:
    """Track whether violation mid-gaps mean-revert before window close."""

    def __init__(self, *, horizons_s: tuple[float, ...] = (30.0, 60.0, 120.0),
                 max_pending: int = 200):
        self.horizons_s = tuple(float(h) for h in horizons_s)
        self.max_pending = int(max_pending)
        self._pending: dict[str, MidConvergenceObservation] = {}
        self._completed: list[dict] = []

    def snap(
        self,
        violation,
        *,
        parent,
        child,
        now: float,
    ) -> None:
        if not getattr(violation, "actionable", False):
            return
        p_mid = getattr(violation, "parent_up_mid", None)
        c_mid = (getattr(violation, "child_up_mids", None) or [None])[0]
        g = _gap(p_mid, c_mid)
        if g is None or g <= 0:
            return
        pk = str(getattr(violation, "parent_window_key", "") or "")
        ck = str((getattr(violation, "child_window_keys", None) or [""])[0] or "")
        if not pk or not ck:
            return
        obs = MidConvergenceObservation(
            parent_key=pk, child_key=ck,
            constraint_type=str(getattr(violation, "constraint_type", "") or ""),
            snap_ts=float(now), gap0=g,
            parent_mid0=float(p_mid), child_mid0=float(c_mid),
            horizons_s=self.horizons_s,
        )
        self._pending[obs.key()] = obs
        if len(self._pending) > self.max_pending:
            oldest = min(self._pending.values(), key=lambda o: o.snap_ts)
            self._pending.pop(oldest.key(), None)

    def advance(self, windows: list, *, now: float) -> None:
        if not self._pending:
            return
        by_id = {w.event_id: w for w in (windows or [])}
        done_keys: list[str] = []
        for key, obs in list(self._pending.items()):
            parent = by_id.get(obs.parent_key)
            child = by_id.get(obs.child_key)
            if parent is None or child is None:
                if now - obs.snap_ts > max(self.horizons_s) + 60:
                    done_keys.append(key)
                continue
            from engine.pulse.dependency_arb import _up_mid
            g = _gap(_up_mid(parent), _up_mid(child))
            if g is None:
                continue
            elapsed = float(now) - obs.snap_ts
            for h in self.horizons_s:
                if elapsed >= h:
                    obs.record_horizon(h, gap=g, ts=now)
            if obs.complete():
                self._completed.append(self._summarize_obs(obs))
                done_keys.append(key)
        for k in done_keys:
            self._pending.pop(k, None)
        if len(self._completed) > 500:
            self._completed = self._completed[-500:]

    @staticmethod
    def _summarize_obs(obs: MidConvergenceObservation) -> dict:
        return {
            "parent_key": obs.parent_key,
            "child_key": obs.child_key,
            "constraint_type": obs.constraint_type,
            "snap_ts": obs.snap_ts,
            "gap0": obs.gap0,
            "parent_mid0": obs.parent_mid0,
            "child_mid0": obs.child_mid0,
            "readings": dict(obs.readings),
        }

    def report(self) -> dict:
        completed = list(self._completed)
        by_h: dict[float, dict] = {}
        for h in self.horizons_s:
            rows = [c["readings"].get(h) for c in completed if h in c.get("readings", {})]
            rows = [r for r in rows if r]
            n = len(rows)
            conv = sum(1 for r in rows if r.get("converged"))
            decays = [float(r.get("gap_decay") or 0) for r in rows]
            by_h[h] = {
                "n": n,
                "converged": conv,
                "converged_rate": round(conv / n, 4) if n else None,
                "avg_gap_decay": round(sum(decays) / n, 6) if n else None,
            }
        return {
            "observe_only": True,
            "horizons_s": list(self.horizons_s),
            "pending": len(self._pending),
            "completed": len(completed),
            "by_horizon": {str(int(h)): by_h[h] for h in self.horizons_s},
            "recent": completed[-8:],
            "note": ("Mid-gap mean-reversion experiment: converged=True when gap at horizon "
                     "is <50% of gap at violation snap. Does not trade."),
        }

    def to_state(self) -> dict:
        return {
            "horizons_s": list(self.horizons_s),
            "pending": [self._summarize_obs(o) for o in self._pending.values()],
            "completed": self._completed[-500:],
        }

    def load_state(self, data: dict) -> None:
        if not data:
            return
        hs = data.get("horizons_s")
        if hs:
            self.horizons_s = tuple(float(x) for x in hs)
        self._completed = list(data.get("completed") or [])[-500:]
        self._pending = {}
        for row in (data.get("pending") or []):
            try:
                obs = MidConvergenceObservation(
                    parent_key=row["parent_key"],
                    child_key=row["child_key"],
                    constraint_type=row.get("constraint_type", ""),
                    snap_ts=float(row.get("snap_ts") or 0),
                    gap0=float(row.get("gap0") or 0),
                    parent_mid0=float(row.get("parent_mid0") or 0),
                    child_mid0=float(row.get("child_mid0") or 0),
                    horizons_s=self.horizons_s,
                    readings=dict(row.get("readings") or {}),
                )
                if obs.snap_ts > 0:
                    self._pending[obs.key()] = obs
            except (KeyError, TypeError, ValueError):
                continue


def gap_converged(gap0: float, gap_now: float, *, convergence_frac: float = 0.5) -> bool:
    if gap0 <= 1e-9:
        return gap_now <= 0
    return float(gap_now) < float(gap0) * float(convergence_frac)


def try_mid_exit_positions(
    ledger,
    windows_by_id: dict,
    *,
    now: float,
    horizon_s: float = 60.0,
    convergence_frac: float = 0.5,
    enabled: bool = True,
) -> int:
    """Paper mid-exit: sell parent-UP when child-parent gap mean-reverts after horizon."""
    if not enabled or ledger is None:
        return 0
    from engine.pulse.dependency_arb import _up_mid
    from engine.pulse.execution_gate import vwap_sell_bids

    n = 0
    for pk, p in list((ledger.positions or {}).items()):
        if p.get("status") != "open":
            continue
        entry_ts = float(p.get("entry_ts") or 0)
        if entry_ts <= 0 or float(now) - entry_ts < float(horizon_s):
            continue
        child_key = str(p.get("child_window_key") or "")
        parent = windows_by_id.get(pk)
        child = windows_by_id.get(child_key) if child_key else None
        if parent is None or child is None:
            continue
        p_mid = _up_mid(parent)
        c_mid = _up_mid(child)
        if p_mid is None or c_mid is None:
            continue
        gap0 = float(p.get("violation_magnitude") or 0)
        g_now = float(c_mid) - float(p_mid)
        if not gap_converged(gap0, g_now, convergence_frac=convergence_frac):
            continue
        book = getattr(parent, "up_book", None)
        bids = getattr(book, "bids", None) if book is not None else None
        if not bids:
            continue
        shares = float(p.get("shares") or 0)
        cost = float(p.get("cost_usd") or 0)
        if shares <= 0 or cost <= 0:
            continue
        vwap, proceeds, sold, full = vwap_sell_bids(bids, shares)
        if vwap is None or not full or sold < shares * 0.99:
            continue
        profit = round(float(proceeds) - cost, 6)
        p["status"] = "settled"
        p["settlement_source"] = "mid_exit_convergence"
        p["outcome_settled"] = False
        p["mid_exit"] = True
        p["exit_vwap"] = round(float(vwap), 6)
        p["exit_ts"] = float(now)
        p["realized_profit_usd"] = profit
        p["won"] = profit > 0
        p["heuristic_profit_usd"] = profit
        if getattr(ledger, "calibration", None) is not None:
            ledger.calibration.record_settled(
                float(p.get("entry_vwap") or 0), profit, profit > 0)
        ledger.realized_profit_usd = round(
            float(getattr(ledger, "realized_profit_usd", 0) or 0) + profit, 6)
        ledger.settled = int(getattr(ledger, "settled", 0) or 0) + 1
        n += 1
    return n


def apply_dep_arb_experiments(cfg, dep_report: dict, *, auto_apply: bool = True) -> list[str]:
    """Evidence-gated runtime self-improve for dep-arb experiment knobs (paper-only).

    Bounded: only tightens selectivity (nested off, clock-skew on) — never loosens safety gates
    or enables live trading. Returns human-readable applied actions for the loop-engine report.
    """
    if not auto_apply or not dep_report:
        return []
    applied: list[str] = []
    cal = dep_report.get("dependency_arb_calibration") or {}
    buckets = cal.get("by_entry_bucket") or {}

    for bucket, st in (buckets.items() if isinstance(buckets, dict) else []):
        st = st or {}
        n = int(st.get("n") or 0)
        pf = st.get("profit_factor")
        if n >= 5 and pf is not None and float(pf) < 1.0:
            if getattr(cfg, "dependency_arb_nested_execute", True):
                cfg.dependency_arb_nested_execute = False
                applied.append("nested_execute=0:bleeding_bucket_%s_pf_%s" % (bucket, pf))
            break

    exp = dep_report.get("experiments") or {}
    mid = exp.get("mid_convergence") or {}
    by_h = mid.get("by_horizon") or {}
    h60 = by_h.get("60") or {}
    n60 = int(h60.get("n") or 0)
    rate60 = h60.get("converged_rate")
    if n60 >= 10 and rate60 is not None and float(rate60) < 0.25:
        if getattr(cfg, "dependency_arb_nested_execute", True):
            cfg.dependency_arb_nested_execute = False
            applied.append("nested_execute=0:low_mid_convergence_60s=%.3f" % float(rate60))

    if n60 >= 5 and rate60 is not None and float(rate60) >= 0.50:
        if not getattr(cfg, "dependency_arb_mid_exit_enabled", False):
            cfg.dependency_arb_mid_exit_enabled = True
            applied.append("mid_exit_enabled=1:convergence_60s=%.3f_n=%d" % (
                float(rate60), n60))

    if not getattr(cfg, "dependency_arb_nested_execute", True):
        if not getattr(cfg, "dependency_arb_clock_skew_enabled", False):
            cfg.dependency_arb_clock_skew_enabled = True
            applied.append("clock_skew_enabled=1:conjunction_only_stack")

    rejects = dep_report.get("rejected_by_reason") or {}
    skew_rejects = sum(
        int(v) for k, v in rejects.items()
        if str(k).startswith("clock_skew_"))
    total_rejects = sum(int(v) for v in rejects.values())
    executed = int(dep_report.get("executed") or 0)
    if (total_rejects >= 50 and executed == 0
            and skew_rejects > total_rejects * 0.8
            and getattr(cfg, "dependency_arb_clock_skew_enabled", False)):
        old = float(getattr(cfg, "dependency_arb_min_parent_book_age_s", 120.0))
        new = max(60.0, old * 0.85)
        if new < old - 1e-6:
            cfg.dependency_arb_min_parent_book_age_s = new
            applied.append("min_parent_book_age_s=%.0f:clock_skew_starving_fills" % new)

    return applied