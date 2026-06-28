"""Chainlink BTC/USD — lagging settlement truth (not a leading signal)."""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from typing import Callable

BTC_USD_FEED = "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
_LATEST_ROUND_DATA = "0xfeaf968c"
DEFAULT_RPCS = (
    "https://ethereum-rpc.publicnode.com",
    "https://1rpc.io/eth",
    "https://cloudflare-eth.com",
)


@dataclass(frozen=True)
class ChainlinkSample:
    price: float
    updated_at: int
    recv_ms: int
    tier: str = "settlement"

    def age_ms(self, now_ms: int) -> int:
        return max(0, now_ms - self.recv_ms)


def _post_json(url: str, payload: dict, timeout: float) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "grok-bot-1/0.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _to_signed(word: int, bits: int = 256) -> int:
    if word >= (1 << (bits - 1)):
        return word - (1 << bits)
    return word


def parse_latest_round_data(hex_data: str, decimals: int = 8) -> dict | None:
    if not hex_data:
        return None
    h = hex_data[2:] if hex_data.startswith("0x") else hex_data
    if len(h) < 64 * 5:
        return None
    words = [int(h[i * 64 : (i + 1) * 64], 16) for i in range(5)]
    answer = _to_signed(words[1])
    updated_at = words[3]
    if answer <= 0:
        return None
    return {"price": answer / (10**decimals), "updated_at": updated_at}


class ChainlinkReader:
    """Fail-closed settlement reader. Returns None on any RPC/parse error."""

    def __init__(
        self,
        rpc_urls: list[str] | None = None,
        timeout: float = 6.0,
        max_age_ms: int = 120_000,
        http: Callable[[str, dict, float], dict] | None = None,
    ) -> None:
        self.rpc_urls = rpc_urls or list(DEFAULT_RPCS)
        self.timeout = timeout
        self.max_age_ms = max_age_ms
        self._http = http or _post_json

    def read(self, now_ms: int | None = None) -> ChainlinkSample | None:
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_call",
            "params": [{"to": BTC_USD_FEED, "data": _LATEST_ROUND_DATA}, "latest"],
        }
        for url in self.rpc_urls:
            try:
                resp = self._http(url, payload, self.timeout)
                decoded = parse_latest_round_data(resp.get("result", ""))
                if not decoded:
                    continue
                age = (now_ms // 1000 - decoded["updated_at"]) * 1000
                if age > self.max_age_ms:
                    continue
                return ChainlinkSample(
                    price=decoded["price"],
                    updated_at=decoded["updated_at"],
                    recv_ms=now_ms,
                )
            except Exception:  # noqa: BLE001
                continue
        return None