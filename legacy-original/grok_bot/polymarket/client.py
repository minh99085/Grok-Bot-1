"""Read-only Polymarket client for btc-updown-5m-* markets."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from grok_bot.polymarket.book import BookSnapshot
from grok_bot.polymarket.market_discovery import WINDOW_MS, MarketDescriptor, slug_for_boundary

GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
PREFIX = "btc-updown-5m-"


def _fetch_json(url: str, timeout: float = 8.0) -> tuple[int | None, Any, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "grok-bot-1/0.2"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read().decode()), None
    except urllib.error.HTTPError as e:
        return e.code, None, f"http_{e.code}"
    except Exception as exc:  # noqa: BLE001
        return None, None, str(exc)


def _coerce_items(data: Any) -> list[dict]:
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for key in ("data", "markets", "events", "results"):
            if isinstance(data.get(key), list):
                return [d for d in data[key] if isinstance(d, dict)]
        return [data]
    return []


def _parse_tokens(item: dict) -> list:
    raw = item.get("clobTokenIds") or item.get("clob_token_ids") or item.get("tokens")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:  # noqa: BLE001
            return []
    return list(raw) if isinstance(raw, list) else []


def _map_up_down(item: dict, tokens: list) -> tuple[str | None, str | None]:
    outcomes = item.get("outcomes")
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except Exception:  # noqa: BLE001
            outcomes = []
    ids = [str(t.get("token_id") or t.get("tokenId") or t) if isinstance(t, dict) else str(t) for t in tokens]
    ids = [i for i in ids if i]
    if len(ids) < 2:
        return None, None
    if outcomes and len(outcomes) >= 2:
        up_i = down_i = None
        for i, o in enumerate(outcomes[: len(ids)]):
            ol = str(o).lower()
            if "up" in ol or "yes" in ol:
                up_i = i
            elif "down" in ol or "no" in ol:
                down_i = i
        if up_i is not None and down_i is not None:
            return ids[up_i], ids[down_i]
    return ids[0], ids[1]


def _window_from_slug(slug: str) -> int | None:
    m = re.search(r"btc-updown-5m-(\d+)", slug)
    return int(m.group(1)) * 1000 if m else None


def parse_market(item: dict) -> MarketDescriptor | None:
    slug = str(item.get("slug") or "")
    if PREFIX not in slug and "btc" not in slug.lower():
        return None
    tokens = _parse_tokens(item)
    up, down = _map_up_down(item, tokens)
    if not up or not down:
        return None
    start = _window_from_slug(slug)
    if start is None:
        return None
    return MarketDescriptor(
        slug=slug,
        condition_id=str(item.get("conditionId") or item.get("condition_id") or ""),
        up_token_id=up,
        down_token_id=down,
        window_start_ms=start,
        window_end_ms=start + WINDOW_MS,
    )


@dataclass
class PolymarketClient:
    gamma: str = GAMMA
    clob: str = CLOB
    fetch: Callable[[str], tuple[int | None, Any, str | None]] = _fetch_json

    def discover_current(self, now_ms: int) -> MarketDescriptor | None:
        slug = slug_for_boundary((now_ms // WINDOW_MS) * WINDOW_MS)
        urls = [
            f"{self.gamma}/markets?slug={urllib.parse.quote(slug)}",
            f"{self.gamma}/events?slug={urllib.parse.quote(slug)}",
        ]
        for url in urls:
            _st, data, err = self.fetch(url)
            if err or not data:
                continue
            for item in _coerce_items(data):
                m = parse_market(item)
                if m:
                    return m
                nested = item.get("markets")
                if isinstance(nested, list):
                    for sub in nested:
                        if isinstance(sub, dict):
                            m = parse_market(sub)
                            if m:
                                return m
        return MarketDescriptor(
            slug=slug,
            condition_id="",
            up_token_id="up",
            down_token_id="down",
            window_start_ms=(now_ms // WINDOW_MS) * WINDOW_MS,
            window_end_ms=(now_ms // WINDOW_MS) * WINDOW_MS + WINDOW_MS,
        )

    def book(self, token_id: str) -> BookSnapshot | None:
        url = f"{self.clob}/book?token_id={urllib.parse.quote(token_id)}"
        _st, data, err = self.fetch(url)
        if err or not isinstance(data, dict):
            return None
        bids = data.get("bids") or []
        asks = data.get("asks") or []
        if not bids or not asks:
            return None
        best_bid = float(bids[0].get("price", bids[0][0] if isinstance(bids[0], list) else 0))
        best_ask = float(asks[0].get("price", asks[0][0] if isinstance(asks[0], list) else 0))
        bid_sz = float(bids[0].get("size", 100) if isinstance(bids[0], dict) else 100)
        ask_sz = float(asks[0].get("size", 100) if isinstance(asks[0], dict) else 100)
        return BookSnapshot(best_bid, best_ask, bid_sz, ask_sz)


class ScriptedPolymarketClient:
    def __init__(self, market: MarketDescriptor, up_mid: float = 0.51) -> None:
        self.market = market
        self.up_mid = up_mid

    def discover_current(self, now_ms: int) -> MarketDescriptor:
        return self.market

    def book(self, token_id: str) -> BookSnapshot:
        if token_id == self.market.up_token_id:
            m = self.up_mid
            return BookSnapshot(m - 0.01, m + 0.01, 500, 500)
        m = 1.0 - self.up_mid
        return BookSnapshot(m - 0.01, m + 0.01, 500, 500)