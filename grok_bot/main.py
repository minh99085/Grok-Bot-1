"""CLI entrypoint for Grok-Bot-1."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from grok_bot.claude_verifier import ClaudeVerifier
from grok_bot.config import BotConfig
from grok_bot.grok_maker import GrokMaker
from grok_bot.pipeline import PipelineContext, build_signal_candidate, verify_with_checker
from grok_bot.safety import LiveTradingDisabledError, submit_order
from loop.connectors.tradingview import TvSignalStore, serve
from loop.driver import DiscoveryLoop
from loop.state import StateManager
from loop.verifier import verify_signal


def _scripted_ingest() -> dict[str, Any]:
    import os
    import time

    from grok_bot.ingest import scripted_ingestor
    from grok_bot.reference_feeds import PriceSample
    from loop.connectors.tradingview import TvSignalStore, parse_alert

    now = int(time.time() * 1000)

    def cex_fn(ts: int):
        return [
            PriceSample("binance", 64120.0, ts, ts),
            PriceSample("coinbase", 64110.0, ts, ts),
        ]

    def chain_http(_url, _payload, _timeout):
        answer = int(64000 * 1e8)
        word = format(answer, "064x")
        updated = format(int(time.time()), "064x")
        return {"result": "0x" + ("0" * 64) + word + ("0" * 64) + updated + ("0" * 64)}

    tv = TvSignalStore(os.devnull)
    tv.add(parse_alert({"symbol": "BTCUSDT", "direction": "UP", "price": 64125.0}, now_ms=now))
    ing = scripted_ingestor(cex_fn=cex_fn, chainlink_fn=chain_http, tv_store=tv, window_start=64000.0)
    data = ing.ingest(now_ms=now)
    data.update(
        sharpe=1.8,
        max_drawdown=0.04,
        newey_west_t=2.5,
        oos_years=2.5,
        notional=100.0,
        min_edge_bps=1.0,
        min_leading_confidence=0.2,
    )
    return data


def _pipeline_propose(data: dict[str, Any]) -> dict[str, Any] | None:
    signal, _ctx = build_signal_candidate(data)
    return signal


def verify() -> int:
    """Offline deterministic checks — no network."""
    checks: dict[str, bool] = {}

    checks["paper_fill_works"] = submit_order({"name": "t"}, paper=True)["paper"] is True
    try:
        submit_order({"name": "t"}, paper=False)
        checks["live_blocked"] = False
    except LiveTradingDisabledError:
        checks["live_blocked"] = True

    good = verify_signal(
        {"sharpe": 2.0, "max_drawdown": 0.05, "newey_west_t": 2.5, "oos_years": 2.5}
    )
    bad = verify_signal({"sharpe": 0.5, "max_drawdown": 0.20, "newey_west_t": 0.5, "oos_years": 0.5})
    checks["verifier_passes_good"] = good.passed
    checks["verifier_rejects_bad"] = not bad.passed

    cfg = BotConfig()
    checks["config_loads"] = cfg.paper_only is True

    claude = ClaudeVerifier(
        api_key="test",
        transport=lambda _k, _m, _s, _u: {"approved": True, "reasons": [], "confidence": 0.9},
    )
    verdict, _ = verify_with_checker(
        {"sharpe": 2.0, "max_drawdown": 0.05, "newey_west_t": 2.5, "oos_years": 2.5},
        PipelineContext(
            market={}, tv_signal=None, maker=None, numeric_verdict=None, claude_review=None
        ),
        claude=claude,
    )
    checks["claude_checker_path"] = verdict.passed

    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        loop = DiscoveryLoop(state_mgr=mgr, ingest=_scripted_ingest, propose=_pipeline_propose)
        results = loop.run_cycle()
        state = mgr.read()
        checks["cycle_ran"] = len(results) >= 4
        checks["state_persisted"] = state.windows_processed == 1

    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


def discover_once() -> int:
    cfg = BotConfig.from_env()
    mgr = StateManager()
    loop = DiscoveryLoop(state_mgr=mgr, ingest=_scripted_ingest, propose=_pipeline_propose)
    results = loop.run_cycle()
    print(
        json.dumps(
            {
                "llm_roles": cfg.llm_roles(),
                "results": [r.__dict__ for r in results],
                "status": loop.discovery_status(),
            },
            indent=2,
            default=str,
        )
    )
    return 0


def run_tradingview_webhook() -> int:
    cfg = BotConfig.from_env()
    store = TvSignalStore(cfg.tradingview_signals_path)
    httpd = serve(
        store,
        host=cfg.tradingview_host,
        port=cfg.tradingview_port,
        token=cfg.tradingview_webhook_secret,
    )
    path = f"/tv/{cfg.tradingview_webhook_secret}" if cfg.tradingview_webhook_secret else "/"
    print(
        json.dumps(
            {
                "ok": True,
                "host": cfg.tradingview_host,
                "port": cfg.tradingview_port,
                "path": path,
                "symbol": "BTCUSDT",
                "signals_file": cfg.tradingview_signals_path,
            },
            indent=2,
        )
    )
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="grok-bot")
    parser.add_argument("--verify", action="store_true", help="offline safety + loop checks")
    parser.add_argument("--discover-once", action="store_true", help="one paper discovery cycle")
    parser.add_argument(
        "--tradingview-webhook",
        action="store_true",
        help="start BTCUSDT TradingView alert webhook server",
    )
    args = parser.parse_args()

    if args.verify:
        return verify()
    if args.discover_once:
        return discover_once()
    if args.tradingview_webhook:
        return run_tradingview_webhook()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())