"""Cross-window dependency arbitrage (LCMM layer).

Layer 1: deterministic linear constraints (nested 5m inside 15m implication).
Layer 2 (later): Bregman/Frank-Wolfe — gated, not required here.

PAPER ONLY — scanner always on; execution gated by ``execute_enabled``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from engine.pulse.execution_gate import vwap_fill

# Entry-price buckets for outcome-settled calibration (feeds Kelly p_win).
ENTRY_PRICE_BUCKETS: list[tuple[float, float, str]] = [
    (0.0, 0.10, "0-0.10"),
    (0.10, 0.20, "0.10-0.20"),
    (0.20, 0.35, "0.20-0.35"),
    (0.35, 0.50, "0.35-0.50"),
    (0.50, 1.01, ">0.50"),
]

DEP_ARB_KELLY_MIN_SAMPLES = 20


def entry_price_bucket(entry_vwap: float) -> str:
    e = float(entry_vwap or 0)
    for lo, hi, label in ENTRY_PRICE_BUCKETS:
        if lo <= e < hi:
            return label
    return ">0.50"


def outcome_settled_pnl(trade: dict, *, outcome_up: bool) -> float:
    """True P&L from parent-UP resolution: win pays $1/share, lose forfeits cost."""
    shares = float(trade.get("shares") or 0)
    cost = float(trade.get("cost_usd") or 0)
    if outcome_up:
        return round(shares * 1.0 - cost, 6)
    return round(-cost, 6)


@dataclass
class DependencyArbCalibration:
    """Per entry-price bucket stats from outcome-settled positions (Kelly p_win source)."""

    buckets: dict = field(default_factory=dict)

    def _bucket(self, label: str) -> dict:
        b = self.buckets.setdefault(label, {
            "n": 0, "wins": 0, "win_rate": None, "avg_pnl": None,
            "profit_factor": None, "gross_win": 0.0, "gross_loss": 0.0,
            "last_won": None,
        })
        return b

    def record_settled(self, entry_vwap: float, pnl: float, won: bool) -> None:
        label = entry_price_bucket(entry_vwap)
        b = self._bucket(label)
        b["n"] += 1
        if won:
            b["wins"] += 1
            if pnl > 0:
                b["gross_win"] = round(float(b["gross_win"]) + pnl, 6)
        elif pnl < 0:
            b["gross_loss"] = round(float(b["gross_loss"]) + (-pnl), 6)
        b["last_won"] = bool(won)
        n = b["n"]
        b["_pnl_sum"] = round(float(b.get("_pnl_sum", 0.0)) + pnl, 6)
        b["win_rate"] = round(b["wins"] / n, 4) if n else None
        b["avg_pnl"] = round(b["_pnl_sum"] / n, 6) if n else None
        gw, gl = float(b["gross_win"]), float(b["gross_loss"])
        if gl > 0:
            b["profit_factor"] = round(gw / gl, 4)
        elif gw > 0:
            b["profit_factor"] = 999.0
        else:
            b["profit_factor"] = None

    def bucket_stats(self, entry_vwap: float) -> dict:
        label = entry_price_bucket(entry_vwap)
        b = self.buckets.get(label)
        if not b:
            return {"bucket": label, "n": 0, "wins": 0, "win_rate": None,
                    "avg_pnl": None, "profit_factor": None, "last_won": None}
        out = {k: v for k, v in b.items() if not str(k).startswith("_")}
        out["bucket"] = label
        return out

    def report(self) -> dict:
        return {
            "buckets": {
                label: {k: v for k, v in b.items() if not str(k).startswith("_")}
                for label, b in self.buckets.items()
            },
            "min_samples_kelly": DEP_ARB_KELLY_MIN_SAMPLES,
        }

    def to_state(self) -> dict:
        return {"buckets": {k: dict(v) for k, v in self.buckets.items()}}

    def load_state(self, data: dict) -> None:
        if not data:
            return
        self.buckets = dict(data.get("buckets") or {})


def compute_dependency_arb_trade_usd(
    *,
    entry_vwap: float,
    max_usd: float,
    book,
    kelly_enabled: bool,
    kelly_fraction: float,
    kelly_depth_frac: float,
    calibration: Optional[DependencyArbCalibration],
    walk_forward_passed: bool,
    kelly_min_samples: int = DEP_ARB_KELLY_MIN_SAMPLES,
) -> float:
    """Edge-proportional sizing; flat max_usd when Kelly off, cold-start, or gate blocked."""
    flat = float(max_usd)
    if not kelly_enabled:
        return flat

    stats = calibration.bucket_stats(entry_vwap) if calibration else {}
    n = int(stats.get("n") or 0)
    if n < kelly_min_samples or not walk_forward_passed:
        return flat

    p_win = float(stats.get("win_rate") or 0)
    edge_per_share = p_win * 1.0 - float(entry_vwap)
    if edge_per_share <= 0:
        return 0.0

    if stats.get("last_won") is False:
        return flat

    depth = float(getattr(book, "ask_depth_usd", 0) or flat)
    depth_cap = max(depth * float(kelly_depth_frac), 1.0)
    fill_probability = min(1.0, depth_cap / max(flat, 1.0))

    from engine.pulse.bregman_projection import modified_kelly_arb_size_usd
    raw = modified_kelly_arb_size_usd(
        edge_per_share=edge_per_share,
        fill_probability=fill_probability,
        max_usd=flat,
        depth_cap_usd=depth_cap,
    )
    trade_usd = float(kelly_fraction) * raw
    return round(min(max(0.0, trade_usd), flat, depth_cap), 4)


def realized_dependency_profit_usd(trade: dict) -> float:
    """VWAP- and ROI-bounded paper profit for nested implication (not raw mid-gap × shares)."""
    shares = float(trade.get("shares") or 0)
    entry = float(trade.get("entry_vwap") or 0)
    cost = float(trade.get("cost_usd") or 0)
    mag = float(trade.get("violation_magnitude") or 0)
    implied = float(trade.get("implied_bound") or (entry + mag))
    cap_frac = float(trade.get("capture_frac") or 0.5)
    expected = float(trade.get("expected_profit_usd") or 0)
    if shares <= 0 or mag <= 0:
        return 0.0
    vwap_edge = max(0.0, implied - entry)
    per_share = min(mag, vwap_edge) * cap_frac
    raw = shares * per_share
    roi_cap = cost * mag * cap_frac
    capped = min(raw, roi_cap)
    if expected > 0:
        capped = min(capped, expected)
    return round(max(0.0, capped), 6)


@dataclass
class DependencyViolation:
    """A detected LCMM constraint violation (may or may not be executable)."""
    constraint_type: str
    parent_window_key: str
    child_window_keys: list
    description: str
    parent_up_mid: Optional[float] = None
    child_up_mids: list = field(default_factory=list)
    implied_bound: Optional[float] = None
    violation_magnitude: float = 0.0
    actionable: bool = False
    reason: str = "log_only"

    def to_dict(self) -> dict:
        return {"constraint_type": self.constraint_type,
                "parent_window_key": self.parent_window_key,
                "child_window_keys": list(self.child_window_keys),
                "description": self.description,
                "parent_up_mid": self.parent_up_mid,
                "child_up_mids": list(self.child_up_mids),
                "implied_bound": self.implied_bound,
                "violation_magnitude": round(self.violation_magnitude, 6),
                "actionable": self.actionable, "reason": self.reason}


def _up_mid(window) -> Optional[float]:
    book = getattr(window, "up_book", None)
    if book is None:
        return None
    return getattr(book, "mid", None)


def group_nested_windows(windows: list) -> list:
    """Group 5m windows whose open_ts falls inside a 15m parent's [open, close)."""
    parents = [w for w in windows if int(getattr(w, "window_seconds", 0) or 0) >= 900]
    children = [w for w in windows if int(getattr(w, "window_seconds", 0) or 0) < 900]
    groups = []
    for p in parents:
        nested = [c for c in children
                  if float(p.open_ts) <= float(c.open_ts) < float(p.close_ts)]
        if nested:
            groups.append((p, sorted(nested, key=lambda x: x.open_ts)))
    return groups


def validate_violation(v: DependencyViolation) -> tuple[bool, str]:
    """Deterministic validator — LLM proposals must pass this before any trade."""
    if v.constraint_type != "nested_implication":
        return False, "unsupported_constraint"
    if v.violation_magnitude <= 0:
        return False, "no_magnitude"
    if not v.parent_window_key or not v.child_window_keys:
        return False, "missing_window_keys"
    if v.parent_up_mid is None or not v.child_up_mids:
        return False, "missing_prices"
    if float(v.child_up_mids[0]) <= float(v.parent_up_mid):
        return False, "implication_not_violated"
    return True, "ok"


def enrich_vwap_actionable(
    violation: DependencyViolation,
    parent,
    child,
    *,
    max_usd: float = 50.0,
    epsilon: float = 0.02,
    capture_frac: float = 0.5,
) -> DependencyViolation:
    """Mark violation actionable when VWAP-executable parent-UP buy clears epsilon."""
    ok, val_reason = validate_violation(violation)
    if not ok:
        violation.actionable = False
        violation.reason = val_reason
        return violation
    trade, fail_reason = try_execute_nested_implication(
        parent, child, violation, max_usd=max_usd, epsilon=epsilon,
        capture_frac=capture_frac, return_reason=True)
    if trade is None or float(trade.get("expected_profit_usd") or 0.0) <= 0:
        violation.actionable = False
        violation.reason = fail_reason or "vwap_not_executable"
        return violation
    violation.actionable = True
    violation.reason = "vwap_executable"
    return violation


def scan_nested_implication(
    parent,
    children: list,
    *,
    epsilon: float = 0.02,
    max_usd: float = 50.0,
    vwap_enrich: bool = True,
) -> list:
    """LCMM: P(up over 15m) >= max P(up over constituent 5m windows) on mids."""
    out = []
    p_mid = _up_mid(parent)
    if p_mid is None:
        return out
    for c in children:
        c_mid = _up_mid(c)
        if c_mid is None:
            continue
        mag = float(c_mid) - float(p_mid)
        if mag > float(epsilon):
            v = DependencyViolation(
                constraint_type="nested_implication",
                parent_window_key=str(parent.event_id),
                child_window_keys=[str(c.event_id)],
                description=("15m up-mid below nested 5m up-mid: "
                             "P(up_15m) cannot be < P(up_5m) for overlapping window"),
                parent_up_mid=round(float(p_mid), 6),
                child_up_mids=[round(float(c_mid), 6)],
                implied_bound=round(float(c_mid), 6),
                violation_magnitude=round(mag, 6),
                actionable=False,
                reason="detected",
            )
            if vwap_enrich:
                v = enrich_vwap_actionable(
                    v, parent, c, max_usd=max_usd, epsilon=epsilon)
            out.append(v)
    return out


def scan_windows(
    windows: list,
    *,
    epsilon: float = 0.02,
    max_usd: float = 50.0,
    vwap_enrich: bool = True,
) -> list:
    """Run all LCMM dependency scans with optional VWAP executability enrichment."""
    violations = []
    for parent, children in group_nested_windows(windows):
        violations.extend(scan_nested_implication(
            parent, children, epsilon=epsilon, max_usd=max_usd,
            vwap_enrich=vwap_enrich))
    return violations


def try_execute_nested_implication(
    parent,
    child,
    violation: DependencyViolation,
    *,
    max_usd: float = 50.0,
    epsilon: float = 0.02,
    capture_frac: float = 0.5,
    bregman_diag: Optional[dict] = None,
    bregman_authority: bool = False,
    kelly_enabled: bool = False,
    kelly_fraction: float = 0.25,
    kelly_depth_frac: float = 0.5,
    calibration: Optional[DependencyArbCalibration] = None,
    walk_forward_passed: bool = False,
    s_open: Optional[float] = None,
    return_reason: bool = False,
) -> Optional[dict]:
    """Paper BUY parent UP when nested implication violated (parent UP underpriced vs child).

    Conservative paper model: expected edge = violation_magnitude * shares * capture_frac,
    booked at parent window close. Deterministic validator must pass first.
    """
    fail = "vwap_not_executable"

    def _ret(trade: Optional[dict], reason: str = "ok"):
        if return_reason:
            return trade, (reason if trade is None else "ok")
        return trade

    ok, reason = validate_violation(violation)
    if not ok:
        return _ret(None, reason)
    book = getattr(parent, "up_book", None)
    if book is None or not getattr(book, "asks", None):
        return _ret(None, "missing_parent_book")
    if kelly_enabled:
        trade_usd = compute_dependency_arb_trade_usd(
            entry_vwap=float(getattr(book, "best_ask", None) or 0.5),
            max_usd=max_usd,
            book=book,
            kelly_enabled=True,
            kelly_fraction=kelly_fraction,
            kelly_depth_frac=kelly_depth_frac,
            calibration=calibration,
            walk_forward_passed=walk_forward_passed,
        )
        if trade_usd <= 0:
            return _ret(None, "kelly_negative_ev")
    elif bregman_authority and bregman_diag:
        from engine.pulse.bregman_projection import modified_kelly_arb_size_usd
        edge = float(
            bregman_diag.get("max_theoretical_profit_per_share")
            or violation.violation_magnitude)
        depth = float(getattr(book, "ask_depth_usd", 0) or max_usd)
        trade_usd = modified_kelly_arb_size_usd(
            edge_per_share=edge,
            fill_probability=0.85,
            max_usd=max_usd,
            depth_cap_usd=max(depth * 0.5, 1.0),
        )
        if trade_usd <= 0:
            return _ret(None, "bregman_kelly_zero")
        if not bregman_diag.get("actionable_projection"):
            return _ret(None, "bregman_not_actionable")
    else:
        trade_usd = float(max_usd)
    vwap, spent, shares, full = vwap_fill(book.asks, trade_usd)
    if vwap is None:
        return _ret(None, "vwap_fill_failed")
    if not full:
        return _ret(None, "partial_fill")
    if shares <= 0:
        return _ret(None, "zero_shares")
    if violation.violation_magnitude < float(epsilon):
        return _ret(None, "below_epsilon")
    expected = round(shares * violation.violation_magnitude * float(capture_frac), 6)
    if expected <= 0:
        return _ret(None, "zero_expected_profit")
    if kelly_enabled:
        entry_mode = "dependency_kelly"
    elif bregman_authority:
        entry_mode = "dependency_bregman"
    else:
        entry_mode = "lcmm_nested"
    implied_bound = float(violation.implied_bound or violation.child_up_mids[0])
    trade = {
        "constraint_type": violation.constraint_type,
        "parent_window_key": str(parent.event_id),
        "parent_market_id": str(getattr(parent, "market_id", "") or ""),
        "child_window_key": str(child.event_id),
        "up_token_id": str(getattr(parent, "up_token_id", "") or ""),
        "down_token_id": str(getattr(parent, "down_token_id", "") or ""),
        "side": "buy_parent_up",
        "entry_mode": entry_mode,
        "shares": round(shares, 4),
        "cost_usd": round(spent, 4),
        "entry_vwap": round(vwap, 6),
        "trade_usd": round(trade_usd, 4),
        "expected_profit_usd": expected,
        "theoretical_profit_usd": expected,
        "capture_frac": float(capture_frac),
        "implied_bound": round(implied_bound, 6),
        "close_ts": float(parent.close_ts),
        "violation_magnitude": violation.violation_magnitude,
        "reason": entry_mode,
        "bregman_projection_distance": (bregman_diag or {}).get("projection_distance"),
        "s_open": s_open,
        "s_close": None,
        "close_lag_s": None,
        "kelly_enabled": bool(kelly_enabled),
    }
    trade["heuristic_profit_usd"] = realized_dependency_profit_usd(trade)
    trade["booked_profit_usd"] = trade["heuristic_profit_usd"]
    return _ret(trade, "ok")


class DependencyArbLedger:
    """Separate ledger for dependency-arb (never blended with dutch-book or directional)."""

    def __init__(
        self,
        *,
        execute_enabled: bool = False,
        kelly_enabled: bool = False,
        kelly_fraction: float = 0.25,
        kelly_depth_frac: float = 0.5,
    ):
        self.execute_enabled = bool(execute_enabled)
        self.kelly_enabled = bool(kelly_enabled)
        self.kelly_fraction = float(kelly_fraction)
        self.kelly_depth_frac = float(kelly_depth_frac)
        self.scans = 0
        self.violations_detected = 0
        self.actionable_detected = 0
        self.executed = 0
        self.settled = 0
        self.realized_profit_usd = 0.0
        self.last_violations: list = []
        self.positions: dict = {}
        self.rejected_invalid = 0
        self.rejected_by_reason: dict = {}
        self.mid_only_violations = 0
        self.calibration = DependencyArbCalibration()

    def record_scan(self, violations: list) -> None:
        self.scans += 1
        self.last_violations = [v.to_dict() if hasattr(v, "to_dict") else dict(v)
                              for v in (violations or [])]
        self.violations_detected += len(self.last_violations)
        self.actionable_detected += sum(
            1 for v in (violations or []) if bool(getattr(v, "actionable", False)))
        for v in (violations or []):
            actionable = bool(getattr(v, "actionable", False))
            reason = str(getattr(v, "reason", "") or "unknown")
            if actionable:
                continue
            if reason == "detected":
                self.mid_only_violations += 1
                reason = "mid_only_pending_vwap"
            self.rejected_by_reason[reason] = (
                int(self.rejected_by_reason.get(reason, 0) or 0) + 1)

    def has_open(self, parent_key: str) -> bool:
        return parent_key in self.positions

    def book(self, trade: dict, *, now: float) -> bool:
        if not self.execute_enabled or not trade:
            return False
        pk = str(trade.get("parent_window_key") or "")
        if not pk or pk in self.positions:
            return False
        self.positions[pk] = {**trade, "status": "open", "entry_ts": float(now)}
        self.executed += 1
        return True

    def settle_due(
        self,
        now: float,
        *,
        resolver: Optional[Callable[[dict, float], tuple[Optional[bool], str]]] = None,
    ) -> int:
        n = 0
        for pk, p in list(self.positions.items()):
            if p.get("status") != "open" or now < float(p.get("close_ts") or 0):
                continue
            outcome_up: Optional[bool] = None
            source = "heuristic"
            if resolver is not None:
                outcome_up, source = resolver(p, now)
                if outcome_up is None:
                    continue
            p["status"] = "settled"
            p["heuristic_profit_usd"] = realized_dependency_profit_usd(p)
            if outcome_up is not None:
                profit = outcome_settled_pnl(p, outcome_up=bool(outcome_up))
                p["won"] = bool(outcome_up)
                p["outcome_up"] = bool(outcome_up)
                p["settlement_source"] = source
                p["outcome_settled"] = True
            else:
                profit = p["heuristic_profit_usd"]
                p["won"] = profit > 0
                p["outcome_settled"] = False
            p["realized_profit_usd"] = profit
            p.setdefault("theoretical_profit_usd", p.get("expected_profit_usd"))
            self.calibration.record_settled(
                float(p.get("entry_vwap") or 0), profit, bool(p.get("won")))
            self.realized_profit_usd = round(self.realized_profit_usd + profit, 6)
            self.settled += 1
            n += 1
        return n

    def _normalize_position(self, p: dict) -> dict:
        """Backfill Roan booking fields and re-apply settlement on load."""
        pos = dict(p)
        entry = float(pos.get("entry_vwap") or 0)
        mag = float(pos.get("violation_magnitude") or 0)
        if not pos.get("implied_bound") and entry and mag:
            pos["implied_bound"] = round(entry + mag, 6)
        pos.setdefault("capture_frac", 0.5)
        pos.setdefault("theoretical_profit_usd", pos.get("expected_profit_usd"))
        pos.setdefault("heuristic_profit_usd", realized_dependency_profit_usd(pos))
        if pos.get("status") == "settled" and not pos.get("outcome_settled"):
            pos["realized_profit_usd"] = pos["heuristic_profit_usd"]
        return pos

    def _recompute_realized_totals(self) -> None:
        total = sum(
            float(p.get("realized_profit_usd") or 0)
            for p in self.positions.values()
            if p.get("status") == "settled"
        )
        self.realized_profit_usd = round(total, 6)

    def _booking_summary(self) -> dict:
        settled = [p for p in self.positions.values() if p.get("status") == "settled"]
        theoretical = round(sum(float(p.get("theoretical_profit_usd")
                                    or p.get("expected_profit_usd") or 0) for p in settled), 4)
        realized = round(sum(float(p.get("realized_profit_usd") or 0) for p in settled), 4)
        ratio = round(realized / theoretical, 4) if theoretical > 0 else None
        return {
            "theoretical_settled_usd": theoretical,
            "realized_settled_usd": realized,
            "capture_ratio": ratio,
            "settled_n": len(settled),
        }

    def _kelly_gate_status(self, walk_forward: Optional[dict] = None) -> dict:
        wf = walk_forward or {}
        passed = bool(wf.get("passed"))
        warm_buckets = sum(
            1 for b in (self.calibration.buckets or {}).values()
            if int(b.get("n") or 0) >= DEP_ARB_KELLY_MIN_SAMPLES)
        return {
            "kelly_enabled": self.kelly_enabled,
            "kelly_active": bool(
                self.kelly_enabled and passed and warm_buckets > 0),
            "walk_forward_passed": passed,
            "walk_forward": wf,
            "warm_buckets": warm_buckets,
            "kelly_fraction": self.kelly_fraction,
            "kelly_depth_frac": self.kelly_depth_frac,
        }

    def report(self, *, walk_forward: Optional[dict] = None) -> dict:
        mode = "paper_execute" if self.execute_enabled else "log_only"
        gate = self._kelly_gate_status(walk_forward)
        return {"strategy": "dependency_arbitrage", "paper_only": True,
                "enabled": self.execute_enabled, "mode": mode,
                "scans": self.scans, "violations_detected": self.violations_detected,
                "actionable_detected": int(getattr(self, "actionable_detected", 0) or 0),
                "rejected_invalid": self.rejected_invalid,
                "rejected_by_reason": dict(self.rejected_by_reason),
                "mid_only_violations": int(getattr(self, "mid_only_violations", 0) or 0),
                "executed": self.executed, "settled": self.settled,
                "open": sum(1 for p in self.positions.values() if p.get("status") == "open"),
                "realized_profit_usd": round(self.realized_profit_usd, 4),
                "booking": self._booking_summary(),
                "dependency_arb_calibration": self.calibration.report(),
                "kelly_active": gate["kelly_active"],
                "kelly_gate": gate,
                "last_violations": self.last_violations[-20:],
                "segregated_from_directional": True,
                "note": ("LCMM nested-window scanner + optional paper execution on validated "
                         "nested_implication violations; outcome-settled P&L + optional Kelly.")}

    def to_state(self) -> dict:
        return {"execute_enabled": self.execute_enabled, "scans": self.scans,
                "violations_detected": self.violations_detected,
                "rejected_invalid": self.rejected_invalid,
                "rejected_by_reason": dict(self.rejected_by_reason),
                "mid_only_violations": int(getattr(self, "mid_only_violations", 0) or 0),
                "executed": self.executed, "settled": self.settled,
                "realized_profit_usd": self.realized_profit_usd,
                "last_violations": self.last_violations,
                "calibration": self.calibration.to_state(),
                "positions": {k: dict(v) for k, v in self.positions.items()}}

    def load_state(self, data: dict) -> None:
        if not data:
            return
        # execute_enabled is set from PulseConfig after load — do not restore from disk.
        self.scans = int(data.get("scans", 0) or 0)
        self.violations_detected = int(data.get("violations_detected", 0) or 0)
        self.rejected_invalid = int(data.get("rejected_invalid", 0) or 0)
        self.rejected_by_reason = dict(data.get("rejected_by_reason") or {})
        self.mid_only_violations = int(data.get("mid_only_violations", 0) or 0)
        self.executed = int(data.get("executed", 0) or 0)
        self.settled = int(data.get("settled", 0) or 0)
        self.last_violations = list(data.get("last_violations") or [])
        self.positions = {
            k: self._normalize_position(v)
            for k, v in (data.get("positions") or {}).items()
        }
        self.calibration.load_state(data.get("calibration") or {})
        self._rebuild_calibration_from_settled()
        self._recompute_realized_totals()

    def _rebuild_calibration_from_settled(self) -> None:
        """Rebuild bucket stats from outcome-settled positions after state load."""
        if self.calibration.buckets:
            return
        for p in self.positions.values():
            if p.get("status") != "settled" or not p.get("outcome_settled"):
                continue
            self.calibration.record_settled(
                float(p.get("entry_vwap") or 0),
                float(p.get("realized_profit_usd") or 0),
                bool(p.get("won")),
            )