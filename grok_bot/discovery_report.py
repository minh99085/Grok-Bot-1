"""Discovery status report — single screen: have we found profit yet?"""

from __future__ import annotations

import json
from pathlib import Path

from loop.discovery_engine import ProfitDiscoveryEngine


def write_discovery_report(engine: ProfitDiscoveryEngine, reports_dir: Path) -> dict:
    reports_dir.mkdir(parents=True, exist_ok=True)
    status = engine.status()
    json_path = reports_dir / "discovery_status.json"
    md_path = reports_dir / "discovery_status.md"

    json_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")

    pf = status.get("portfolio") or {}
    cal = status.get("calibration") or {}
    lines = [
        "# Grok-Bot-1 Profit Discovery Status",
        "",
        f"**Mode:** {status.get('mode', 'profit_discovery')}",
        f"**Rung:** {status.get('status', 'observe')}",
        f"**Headline:** {status.get('headline', '')}",
        "",
        "## Portfolio (paper)",
        f"- Trades: {pf.get('trades', 0)}",
        f"- Total PnL: {pf.get('total_pnl', 0)}",
        f"- Win rate: {pf.get('win_rate')}",
        f"- Profit factor: {pf.get('profit_factor')}",
        "",
        "## Calibration proxy",
        f"- N: {cal.get('n', 0)}",
        f"- Brier proxy: {cal.get('brier_proxy')}",
        f"- Armed: {cal.get('armed', False)}",
        "",
        "## Blockers",
    ]
    blockers = status.get("blockers") or []
    lines.extend(f"- {b}" for b in blockers) if blockers else lines.append("- none")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return status