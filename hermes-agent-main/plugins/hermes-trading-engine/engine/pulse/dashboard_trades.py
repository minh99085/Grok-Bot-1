"""Unified recent-trade rows for the read-only pulse dashboard."""
from __future__ import annotations

from typing import Any


def _sort_ts(row: dict) -> float:
    for key in ("sort_ts", "close_ts", "entry_ts", "open_ts"):
        val = row.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue
    return 0.0


def _directional_row(pos: dict) -> dict:
    row = dict(pos)
    row.setdefault("trade_type", "directional")
    row["sort_ts"] = _sort_ts(row)
    return row


def _dep_arb_row(pos: dict) -> dict:
    status = str(pos.get("status") or "open")
    realized = pos.get("realized_profit_usd")
    expected = pos.get("expected_profit_usd") or pos.get("theoretical_profit_usd")
    pnl = None
    won = None
    if status == "settled" and realized is not None:
        pnl = float(realized)
        won = pnl > 0
    window = str(pos.get("parent_window_key") or pos.get("window_key") or "")
    return {
        "trade_type": "dep_arb",
        "side": "ARB",
        "entry_price": pos.get("entry_vwap"),
        "entry_ts": pos.get("entry_ts"),
        "close_ts": pos.get("close_ts"),
        "sort_ts": float(pos.get("close_ts") or pos.get("entry_ts") or 0),
        "status": status,
        "pnl_usd": pnl,
        "won": won,
        "research": {
            "series_label": "dep-arb",
            "market_series": f"nested {window}" if window else "nested",
        },
        "expected_profit_usd": expected,
    }


def _dutch_arb_row(pos: dict) -> dict:
    status = str(pos.get("status") or "open")
    profit = pos.get("realized_profit_usd")
    if profit is None and status == "settled":
        profit = pos.get("guaranteed_profit_usd")
    pnl = float(profit) if profit is not None and status == "settled" else None
    won = (pnl > 0) if pnl is not None else None
    series = str(pos.get("series_label") or "dutch-arb")
    window = str(pos.get("window_key") or "")
    return {
        "trade_type": "dutch_arb",
        "side": "ARB",
        "entry_price": pos.get("up_vwap"),
        "entry_ts": pos.get("entry_ts"),
        "close_ts": pos.get("close_ts"),
        "sort_ts": float(pos.get("close_ts") or pos.get("entry_ts") or 0),
        "status": status,
        "pnl_usd": pnl,
        "won": won,
        "research": {
            "series_label": series,
            "market_series": window or series,
        },
    }


def recent_trades_for_dashboard(ledger: dict | None, *, limit: int = 20) -> list[dict]:
    """Merge directional, dependency-arb, and dutch-book rows for the dashboard sidebar."""
    if not ledger:
        return []

    rows: list[dict] = []
    for pos in ledger.get("positions") or []:
        if isinstance(pos, dict):
            rows.append(_directional_row(pos))

    acct = ledger.get("accounting_state") or {}
    dep = acct.get("dep_arb_ledger") or {}
    for pos in (dep.get("positions") or {}).values():
        if isinstance(pos, dict):
            rows.append(_dep_arb_row(pos))

    arb = acct.get("arb_ledger") or {}
    for pos in (arb.get("positions") or {}).values():
        if isinstance(pos, dict):
            rows.append(_dutch_arb_row(pos))

    rows.sort(key=_sort_ts, reverse=True)
    return rows[: max(1, int(limit))]