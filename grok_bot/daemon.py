"""VPS daemon — profit discovery loop with self-improvement + TradingView webhook."""

from __future__ import annotations

import json
import time
from pathlib import Path

from grok_bot.analyst import run_self_improve_cycle
from grok_bot.config import BotConfig
from grok_bot.discovery_report import write_discovery_report
from grok_bot.evidence import EvidenceStore, WindowRecord
from grok_bot.factory import build_discovery_engine
from grok_bot.risk import risk_check
from grok_bot.window_engine import Btc5mWindowEngine
from loop.connectors.notifier import notify
from loop.connectors.tradingview import TvSignalStore, serve
from loop.state import StateManager


def _start_tradingview_webhook(cfg: BotConfig, store: TvSignalStore) -> str:
    serve(
        store,
        host=cfg.tradingview_host,
        port=cfg.tradingview_port,
        token=cfg.tradingview_webhook_secret,
    )
    if cfg.tradingview_webhook_secret:
        return f"/tv/{cfg.tradingview_webhook_secret}"
    return "/"


def _maybe_self_improve(engine: Btc5mWindowEngine, evidence: EvidenceStore, window_n: int) -> None:
    if window_n % 10 != 0:
        return
    trades = evidence.trade_records()
    if len(trades) < 3:
        return
    result = run_self_improve_cycle(
        trades,
        maker=engine.maker,
        checker=engine.checker,
    )
    if result and result.approved:
        notify(f"self-improve: {result.reason}", level="info")


def run_daemon(cfg: BotConfig | None = None, *, interval_seconds: float = 300.0) -> None:
    cfg = cfg or BotConfig.from_env()
    reports = Path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "loop_state").mkdir(parents=True, exist_ok=True)

    tv_store = TvSignalStore(cfg.tradingview_signals_path)
    webhook_path = _start_tradingview_webhook(cfg, tv_store)
    engine_window = Btc5mWindowEngine(cfg, tv_store=tv_store)

    evidence = EvidenceStore(reports / "windows.jsonl")
    state_mgr = StateManager(reports / "loop_state")
    discovery = build_discovery_engine(cfg, state_root=reports / "loop_state", reports_dir=reports)

    startup = {
        "mode": "profit_discovery",
        "paper_only": cfg.paper_only,
        "llm_roles": cfg.llm_roles(),
        "webhook": f"http://{cfg.tradingview_host}:{cfg.tradingview_port}{webhook_path}",
        "interval_s": interval_seconds,
    }
    notify("Grok-Bot-1 daemon started", level="info")
    print(json.dumps(startup))

    window_n = state_mgr.read().windows_processed

    while True:
        try:
            risk = risk_check(state_mgr)
            if risk.get("halt"):
                notify(f"risk halt: {risk['kill_events']} kill events", level="error")
                break

            outcome = engine_window.run_window()
            window_n += 1
            action = outcome.get("action", "observe")
            data = outcome.get("data") or {}
            pnl = outcome.get("pnl")

            evidence.append(
                WindowRecord(
                    window_id=window_n,
                    ts_ms=int(data.get("ts_ms", time.time() * 1000)),
                    p_up=float(data.get("p_up", 0.5)),
                    edge_bps=float(data.get("edge_bps", 0)),
                    implied_direction=str(data.get("implied_direction", "neutral")),
                    action="paper_fill" if action == "paper_fill" else action,
                    simulated_pnl=float(pnl) if pnl is not None else None,
                    leading_confidence=float(data.get("leading_confidence", 0)),
                )
            )

            state = state_mgr.read()
            state.windows_processed = window_n
            state.mode = "profit_discovery"
            state.last_verdict = action
            discovery_status = discovery.status()
            state.discovery_status = discovery_status["status"]
            state.current_rung = discovery_status["status"]
            state_mgr.write(state)

            write_discovery_report(discovery, reports)
            _maybe_self_improve(engine_window, evidence, window_n)

            if discovery_status.get("any_armed"):
                notify(f"EDGE DISCOVERED: {discovery_status['headline']}", level="armed")
                break

            log = {
                "window": window_n,
                "action": action,
                "rung": discovery_status["status"],
                "headline": discovery_status["headline"],
                "market": outcome.get("market"),
            }
            print(json.dumps(log))

        except Exception as exc:  # noqa: BLE001
            notify(f"daemon error: {exc}", level="error")
            print(json.dumps({"error": str(exc)}))

        time.sleep(interval_seconds)