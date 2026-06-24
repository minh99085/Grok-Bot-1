"""Stage-1 ingest: leading feeds first, Chainlink settlement truth second."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from grok_bot.chainlink_reader import ChainlinkReader
from grok_bot.price_stack import PriceStack
from grok_bot.reference_feeds import CexLeadingFeed, ScriptedCexFeed
from loop.connectors.tradingview import TvSignalStore


@dataclass
class WindowIngestor:
    price_stack: PriceStack
    _window_start: float | None = None
    _history: list[dict[str, Any]] = field(default_factory=list)

    def on_window_open(self, chainlink_open: float | None) -> None:
        self._window_start = chainlink_open

    def ingest(self, *, now_ms: int | None = None) -> dict[str, Any]:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        snap = self.price_stack.snapshot(now_ms, window_start=self._window_start)
        payload = {
            "symbol": "btc-updown-5m",
            "ts_ms": now_ms,
            "window_start": self._window_start,
            "price_stack": snap.as_dict(),
            "p_up": snap.p_up,
            "edge_bps": snap.edge_bps,
            "implied_direction": snap.implied_direction,
            "leading_confidence": snap.leading.confidence,
            "feed_order": ["binance", "coinbase", "tradingview", "chainlink_settlement"],
        }
        self._history.append(payload)
        return payload


def scripted_ingestor(
    *,
    cex_fn,
    chainlink_fn,
    tv_store: TvSignalStore | None = None,
    window_start: float = 64000.0,
) -> WindowIngestor:
    stack = PriceStack(
        cex=ScriptedCexFeed(cex_fn),
        chainlink=ChainlinkReader(http=chainlink_fn),  # type: ignore[arg-type]
        tv_store=tv_store,
    )
    ing = WindowIngestor(price_stack=stack)
    ing.on_window_open(window_start)
    return ing


def live_ingestor(tv_store: TvSignalStore | None = None) -> WindowIngestor:
    return WindowIngestor(
        price_stack=PriceStack(CexLeadingFeed(), ChainlinkReader(), tv_store),
    )