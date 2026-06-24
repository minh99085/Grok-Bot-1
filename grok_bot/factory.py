"""Build profit-discovery runtime from config."""

from __future__ import annotations

import os
from pathlib import Path

from grok_bot.config import BotConfig
from grok_bot.evidence import EvidenceStore
from grok_bot.ingest import live_ingestor, scripted_ingestor
from grok_bot.pipeline import build_signal_candidate
from grok_bot.reference_feeds import PriceSample
from loop.connectors.tradingview import TvSignalStore
from loop.discovery_engine import DiscoveryConfig, ProfitDiscoveryEngine
from loop.driver import DiscoveryLoop
from loop.state import StateManager


def _live_ingest_fn(tv_store: TvSignalStore):
    ing = live_ingestor(tv_store)

    def ingest() -> dict:
        data = ing.ingest()
        data.setdefault("sharpe", 0.0)
        data.setdefault("min_edge_bps", 3.0)
        data.setdefault("min_leading_confidence", 0.35)
        data.setdefault("notional", 100.0)
        return data

    return ingest


def _scripted_ingest_fn():
    import time

    def cex_fn(ts: int):
        return [
            PriceSample("binance", 64100.0 + (ts % 50), ts, ts),
            PriceSample("coinbase", 64095.0 + (ts % 50), ts, ts),
        ]

    def chain_http(_url, _payload, _timeout):
        answer = int(64000 * 1e8)
        word = format(answer, "064x")
        updated = format(int(time.time()), "064x")
        return {"result": "0x" + ("0" * 64) + word + ("0" * 64) + updated + ("0" * 64)}

    ing = scripted_ingestor(cex_fn=cex_fn, chainlink_fn=chain_http, window_start=64000.0)

    def ingest() -> dict:
        data = ing.ingest()
        data.update(sharpe=1.8, max_drawdown=0.04, newey_west_t=2.5, oos_years=2.5,
                    notional=100.0, min_edge_bps=1.0, min_leading_confidence=0.2)
        return data

    return ingest


def build_discovery_engine(
    cfg: BotConfig | None = None,
    *,
    scripted: bool = False,
    state_root: Path | None = None,
    reports_dir: Path | None = None,
) -> ProfitDiscoveryEngine:
    cfg = cfg or BotConfig.from_env()
    reports = reports_dir or Path("reports")
    state_root = state_root or Path("reports/loop_state")

    tv_store = TvSignalStore(cfg.tradingview_signals_path)
    ingest_fn = _scripted_ingest_fn() if scripted else _live_ingest_fn(tv_store)

    def propose(data: dict):
        signal, _ = build_signal_candidate(data)
        return signal

    loop = DiscoveryLoop(state_mgr=StateManager(state_root), ingest=ingest_fn, propose=propose)
    evidence = EvidenceStore(reports / "windows.jsonl")
    discovery_cfg = DiscoveryConfig(
        max_windows=int(os.getenv("DISCOVERY_MAX_WINDOWS", "500")),
        max_seconds=float(os.getenv("DISCOVERY_MAX_SECONDS", "86400")),
    )
    return ProfitDiscoveryEngine(
        loop=loop,
        state_mgr=StateManager(state_root),
        evidence=evidence,
        config=discovery_cfg,
    )