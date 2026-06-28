"""One BTC 5m Polymarket window: ingest → signal → verify → paper execute."""

from __future__ import annotations

import time
from typing import Any

from grok_bot.chainlink_reader import ChainlinkReader
from grok_bot.claude_verifier import ClaudeVerifier
from grok_bot.config import BotConfig
from grok_bot.grok_maker import GrokMaker
from grok_bot.ingest import WindowIngestor
from grok_bot.pipeline import build_signal_candidate, verify_with_checker
from grok_bot.polymarket.client import PolymarketClient

from grok_bot.reference_feeds import CexLeadingFeed
from grok_bot.price_stack import PriceStack
from grok_bot.safety import submit_order
from loop.connectors.tradingview import TvSignalStore
from loop.verifier import verify_signal


class Btc5mWindowEngine:
    def __init__(self, cfg: BotConfig, *, tv_store: TvSignalStore | None = None) -> None:
        self.cfg = cfg
        self.tv_store = tv_store or TvSignalStore(cfg.tradingview_signals_path)
        rpcs = [u.strip() for u in cfg.eth_rpc_urls.split(",") if u.strip()] or None
        self.pm = PolymarketClient()
        self.chainlink = ChainlinkReader(rpc_urls=rpcs, max_age_ms=cfg.chainlink_max_age_ms)
        self.maker = GrokMaker(api_key=cfg.xai_api_key, model=cfg.xai_model)
        self.checker = ClaudeVerifier(api_key=cfg.anthropic_api_key, model=cfg.claude_model)
        self._window_start_price: float | None = None
        self._ingestor = self._build_ingestor()

    def _build_ingestor(self) -> WindowIngestor:
        stack = PriceStack(
            CexLeadingFeed(),
            self.chainlink,
            self.tv_store,
            max_cex_staleness_ms=self.cfg.cex_max_staleness_ms,
        )
        return WindowIngestor(price_stack=stack)

    def run_window(self) -> dict[str, Any]:
        now_ms = int(time.time() * 1000)
        market = self.pm.discover_current(now_ms)
        up_book = self.pm.book(market.up_token_id)
        down_book = self.pm.book(market.down_token_id)

        if self._window_start_price is None or now_ms >= market.window_start_ms:
            cl = self.chainlink.read(now_ms)
            self._window_start_price = cl.price if cl else None
            self._ingestor.on_window_open(self._window_start_price)

        data = self._ingestor.ingest(now_ms=now_ms)
        data.update(
            {
                "market_slug": market.slug,
                "window_start_ms": market.window_start_ms,
                "window_end_ms": market.window_end_ms,
                "up_mid": up_book.mid if up_book else None,
                "down_mid": down_book.mid if down_book else None,
                "min_edge_bps": 3.0,
                "min_leading_confidence": 0.35,
                "sharpe": 1.8 if data.get("edge_bps", 0) > 5 else 0.0,
                "max_drawdown": 0.04,
                "newey_west_t": 2.5,
                "oos_years": 2.5,
                "notional": 100.0,
            }
        )

        signal, ctx = build_signal_candidate(data, tv_store=self.tv_store, maker=self.maker)
        result: dict[str, Any] = {
            "ts_ms": now_ms,
            "market": market.slug,
            "data": data,
            "signal": None,
            "action": "observe",
            "pnl": None,
        }

        if signal is None:
            return result

        numeric = verify_signal(signal)
        if not numeric.passed:
            result["action"] = "rejected_numeric"
            result["reasons"] = numeric.reasons
            return result

        verdict, ctx = verify_with_checker(signal, ctx, claude=self.checker)
        if not verdict.passed:
            result["action"] = "rejected_checker"
            result["reasons"] = verdict.reasons
            result["claude"] = ctx.claude_review
            return result

        side = data.get("implied_direction", "UP")
        if side not in ("UP", "DOWN"):
            result["action"] = "rejected_neutral"
            return result

        fill = submit_order({**signal, "side": side}, paper=True)
        result["action"] = "paper_fill"
        result["signal"] = signal
        result["fill"] = fill
        result["pnl"] = fill.get("pnl")
        result["claude"] = ctx.claude_review
        return result