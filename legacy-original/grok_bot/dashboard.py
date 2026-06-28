"""Read-only web dashboard for paper profit-discovery monitoring."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from grok_bot.config import BotConfig
from grok_bot.evidence import EvidenceStore, portfolio_metrics, promotion_rung
from grok_bot.risk import risk_check
from loop.state import StateManager


def _read_jsonl(path: Path, *, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def build_snapshot(
    *,
    reports_dir: Path = Path("reports"),
    cfg: BotConfig | None = None,
) -> dict[str, Any]:
    cfg = cfg or BotConfig.from_env()
    state_mgr = StateManager(reports_dir / "loop_state")
    state = state_mgr.read()
    evidence = EvidenceStore(reports_dir / "windows.jsonl")
    promo = promotion_rung(evidence.records)

    discovery_path = reports_dir / "discovery_status.json"
    discovery: dict[str, Any] = {}
    if discovery_path.exists():
        try:
            discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            discovery = {}

    action_counts = Counter(r.action for r in evidence.records)
    recent_windows = [
        {
            "window_id": r.window_id,
            "ts_ms": r.ts_ms,
            "action": r.action,
            "direction": r.implied_direction,
            "edge_bps": round(r.edge_bps, 2),
            "p_up": round(r.p_up, 4),
            "pnl": r.simulated_pnl,
            "leading_confidence": round(r.leading_confidence, 3),
        }
        for r in evidence.records[-25:]
    ]

    tv_signals = _read_jsonl(Path(cfg.tradingview_signals_path), limit=10)
    risk = risk_check(state_mgr)

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "generated_ts": int(time.time()),
        "mode": state.mode or discovery.get("mode", "profit_discovery"),
        "rung": promo["rung"],
        "headline": discovery.get("headline") or _headline(promo),
        "any_armed": promo["any_armed"],
        "blockers": promo["blockers"],
        "paper_only": cfg.paper_only,
        "llm_roles": cfg.llm_roles(),
        "windows_processed": state.windows_processed,
        "last_verdict": state.last_verdict,
        "portfolio": promo["portfolio"],
        "calibration": promo["calibration"],
        "action_counts": dict(action_counts),
        "kill_events": state.kill_events[-10:],
        "open_positions": len(state.open_positions),
        "risk": risk,
        "recent_windows": recent_windows,
        "tv_signals": tv_signals[-5:],
        "tv_signal_count": len(_read_jsonl(Path(cfg.tradingview_signals_path), limit=10_000)),
    }


def _headline(promo: dict[str, Any]) -> str:
    if promo["any_armed"]:
        return "EDGE FOUND — strategy reached armed rung"
    pf = promo["portfolio"]
    if pf["trades"]:
        return f"{pf['trades']} paper trades, PnL {pf['total_pnl']}"
    return "observe only — accumulating windows"


def _render_html(snapshot: dict[str, Any]) -> str:
    pf = snapshot.get("portfolio") or {}
    cal = snapshot.get("calibration") or {}
    blockers = snapshot.get("blockers") or []
    rung = snapshot.get("rung", "observe")
    rung_cls = "good" if rung == "armed" else ("warn" if rung == "shadow" else "")
    pnl = pf.get("total_pnl", 0) or 0
    pnl_cls = "good" if pnl > 0 else ("bad" if pnl < 0 else "")

    def chip(label: str, value: str, cls: str = "") -> str:
        c = f" {cls}" if cls else ""
        return f'<span class="chip{c}"><span class="k">{label}</span>{value}</span>'

    chips = "".join(
        [
            chip("Mode", snapshot.get("mode", "—"), "good"),
            chip("Rung", rung, rung_cls or "warn"),
            chip("Paper", "ON" if snapshot.get("paper_only") else "OFF", "good"),
            chip("Maker", (snapshot.get("llm_roles") or {}).get("maker", "—")),
            chip("Checker", (snapshot.get("llm_roles") or {}).get("checker", "—")),
            chip("Windows", str(snapshot.get("windows_processed", 0))),
        ]
    )

    rows = ""
    for w in reversed(snapshot.get("recent_windows") or []):
        pnl_v = w.get("pnl")
        pnl_s = f"{pnl_v:.4f}" if pnl_v is not None else "—"
        rows += (
            f"<tr><td>{w.get('window_id')}</td><td>{w.get('action')}</td>"
            f"<td>{w.get('direction')}</td><td>{w.get('edge_bps')}</td>"
            f"<td>{pnl_s}</td></tr>"
        )
    if not rows:
        rows = '<tr><td colspan="5" style="color:#8b949e">No windows yet</td></tr>'

    blocker_html = "".join(f'<span class="pill">{b}</span>' for b in blockers) or (
        '<span style="color:#56d364">none</span>'
    )

    kill = snapshot.get("kill_events") or []
    kill_html = "".join(f'<span class="pill bad">{k}</span>' for k in kill) or (
        '<span style="color:#56d364">none</span>'
    )

    ac = snapshot.get("action_counts") or {}
    action_pills = "".join(f'<span class="pill">{k}: {v}</span>' for k, v in sorted(ac.items()))
    risk_halt = (snapshot.get("risk") or {}).get("halt")
    cal_armed = "yes" if cal.get("armed") else "no"
    risk_halt_s = "yes" if risk_halt else "no"

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="15">
<title>Grok-Bot-1 — Paper Discovery</title>
<style>
:root{{color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
 background:#0d1117;color:#e6edf3}}
.wrap{{max-width:1100px;margin:0 auto;padding:24px}}
h1{{font-size:20px;margin:0 0 4px}}
.sub{{color:#8b949e;font-size:12px;margin-bottom:20px}}
.chips{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:22px}}
.chip{{padding:8px 14px;border-radius:999px;font-weight:600;font-size:13px;border:1px solid #30363d}}
.chip .k{{color:#8b949e;font-weight:500;margin-right:6px;font-size:11px;text-transform:uppercase;letter-spacing:.04em}}
.good{{background:#0f2417;border-color:#1f6f3f;color:#56d364}}
.warn{{background:#2a2412;border-color:#9e7a1a;color:#e3b341}}
.bad{{background:#2a1416;border-color:#a13b41;color:#f85149}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:18px;margin-bottom:18px}}
.card h2{{font-size:14px;margin:0 0 12px;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}
.m{{display:flex;justify-content:space-between;border-bottom:1px solid #21262d;padding:6px 0}}
.m .lab{{color:#8b949e}}.m .val{{font-weight:600}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:6px 8px;border-bottom:1px solid #21262d;text-align:left}}
th{{color:#8b949e;font-size:11px;text-transform:uppercase}}
.pill{{display:inline-block;padding:2px 8px;border-radius:6px;background:#21262d;margin:2px;font-size:12px}}
.pill.bad{{background:#2a1416;color:#f85149}}
.foot{{color:#8b949e;font-size:12px;margin-top:18px}}
.banner{{padding:10px 14px;border-radius:8px;margin-bottom:18px;font-weight:600;background:#161b22;border:1px solid #30363d}}
</style>
<script>
async function poll() {{
  try {{
    const r = await fetch('/api/status');
    if (r.ok) location.reload();
  }} catch (_) {{}}
}}
setInterval(poll, 15000);
</script>
</head><body><div class="wrap">
<h1>Grok-Bot-1 <span style="color:#8b949e;font-weight:400">paper profit discovery</span></h1>
<div class="sub">updated {snapshot.get("generated_at")} · auto-refresh 15s · read-only</div>
<div class="banner">{snapshot.get("headline", "")}</div>
<div class="chips">{chips}</div>

<div class="card"><h2>Portfolio (paper)</h2><div class="grid">
<div class="m"><span class="lab">Trades</span><span class="val">{pf.get("trades", 0)}</span></div>
<div class="m"><span class="lab">Total PnL</span><span class="val {pnl_cls}">{pnl}</span></div>
<div class="m"><span class="lab">Win rate</span><span class="val">{pf.get("win_rate") or "—"}</span></div>
<div class="m"><span class="lab">Profit factor</span><span class="val">{pf.get("profit_factor") or "—"}</span></div>
<div class="m"><span class="lab">Avg win</span><span class="val">{pf.get("avg_win") or "—"}</span></div>
<div class="m"><span class="lab">Avg loss</span><span class="val">{pf.get("avg_loss") or "—"}</span></div>
</div></div>

<div class="card"><h2>Calibration</h2><div class="grid">
<div class="m"><span class="lab">Sample N</span><span class="val">{cal.get("n", 0)}</span></div>
<div class="m"><span class="lab">Brier proxy</span><span class="val">{cal.get("brier_proxy") or "—"}</span></div>
<div class="m"><span class="lab">Armed</span><span class="val">{cal_armed}</span></div>
<div class="m"><span class="lab">Last verdict</span><span class="val">{snapshot.get("last_verdict", "—")}</span></div>
<div class="m"><span class="lab">TV signals</span><span class="val">{snapshot.get("tv_signal_count", 0)}</span></div>
<div class="m"><span class="lab">Risk halt</span><span class="val">{risk_halt_s}</span></div>
</div></div>

<div class="card"><h2>Blockers</h2>{blocker_html}</div>
<div class="card"><h2>Action counts</h2>{action_pills or '<span style="color:#8b949e">none</span>'}</div>
<div class="card"><h2>Kill events</h2>{kill_html}</div>

<div class="card"><h2>Recent windows</h2>
<table><tr><th>ID</th><th>Action</th><th>Dir</th><th>Edge bps</th><th>PnL</th></tr>
{rows}</table></div>

<div class="foot">Read-only dashboard — no control actions. Live trading structurally disabled.</div>
</div></body></html>"""


def _authorized(path: str, query: str, token: str) -> bool:
    if not token:
        return True
    p = path.rstrip("/")
    if p == f"/dash/{token}" or p == f"/api/status/{token}":
        return True
    qs = parse_qs(query)
    return qs.get("token", [""])[0] == token


def make_handler(
    *,
    reports_dir: Path,
    cfg: BotConfig,
    token: str = "",
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            pass

        def _deny(self) -> None:
            self.send_response(404)
            self.end_headers()

        def _ok_json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, indent=2).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _ok_html(self, html: str) -> None:
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if not _authorized(path, parsed.query, token):
                return self._deny()

            api_paths = {"/api/status", f"/api/status/{token}"} if token else {"/api/status"}
            page_paths = {"/", "/dashboard", f"/dash/{token}"} if token else {"/", "/dashboard"}

            if path in api_paths:
                snap = build_snapshot(reports_dir=reports_dir, cfg=cfg)
                return self._ok_json(snap)
            if path in page_paths:
                snap = build_snapshot(reports_dir=reports_dir, cfg=cfg)
                return self._ok_html(_render_html(snap))
            return self._deny()

    return Handler


def serve_dashboard(
    cfg: BotConfig | None = None,
    *,
    reports_dir: Path | None = None,
) -> ThreadingHTTPServer:
    cfg = cfg or BotConfig.from_env()
    reports = reports_dir or Path(os.getenv("REPORTS_DIR", "reports"))
    httpd = ThreadingHTTPServer(
        (cfg.dashboard_host, cfg.dashboard_port),
        make_handler(reports_dir=reports, cfg=cfg, token=cfg.dashboard_token),
    )
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def dashboard_url(cfg: BotConfig | None = None, *, host: str | None = None) -> str:
    cfg = cfg or BotConfig.from_env()
    h = host or cfg.dashboard_public_host or "127.0.0.1"
    base = f"http://{h}:{cfg.dashboard_port}"
    if cfg.dashboard_token:
        return f"{base}/dash/{cfg.dashboard_token}"
    return base