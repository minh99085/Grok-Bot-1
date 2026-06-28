"""TradingView BTCUSDT alert webhook — observe-only signal feed."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _norm_direction(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in ("up", "long", "buy", "bull", "bullish", "1"):
        return "UP"
    if s in ("down", "short", "sell", "bear", "bearish", "-1"):
        return "DOWN"
    return "unknown"


def _norm_strength(v: Any) -> str:
    if v is None:
        return "unknown"
    if isinstance(v, (int, float)):
        return "strong" if abs(v) >= 2 else "weak"
    s = str(v).strip().lower()
    if s in ("strong", "high", "2", "3"):
        return "strong"
    if s in ("weak", "low", "1"):
        return "weak"
    return s or "unknown"


@dataclass
class TvSignal:
    direction: str
    strength: str
    indicator: str
    received_ms: int
    symbol: str | None = None
    price: float | None = None
    ttc_s: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def level(self) -> str:
        return f"{self.direction}_{self.strength}".upper()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_alert(payload: bytes | str | dict, *, now_ms: int | None = None) -> TvSignal:
    if isinstance(payload, (bytes, bytearray)):
        payload = payload.decode("utf-8", "replace")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {"note": payload}
    if not isinstance(payload, dict):
        payload = {"note": str(payload)}

    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)

    def _num(key: str) -> float | None:
        v = payload.get(key)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    symbol = payload.get("symbol") or payload.get("ticker") or "BTCUSDT"
    return TvSignal(
        direction=_norm_direction(payload.get("direction") or payload.get("side")),
        strength=_norm_strength(payload.get("strength") or payload.get("conviction")),
        indicator=str(payload.get("indicator") or payload.get("study") or "unknown").lower(),
        received_ms=now_ms,
        symbol=str(symbol).upper(),
        price=_num("price"),
        ttc_s=_num("ttc_s") or _num("seconds_to_close"),
        raw=payload,
    )


class TvSignalStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._signals: list[TvSignal] = []

    def add(self, sig: TvSignal) -> TvSignal:
        self._signals.append(sig)
        if self.path and self.path != os.devnull:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(sig.as_dict(), default=str) + "\n")
        return sig

    @property
    def signals(self) -> list[TvSignal]:
        return list(self._signals)

    def latest(self) -> TvSignal | None:
        return self._signals[-1] if self._signals else None

    def latest_for_symbol(self, symbol: str = "BTCUSDT") -> TvSignal | None:
        sym = symbol.upper()
        for sig in reversed(self._signals):
            if (sig.symbol or "").upper() == sym:
                return sig
        return None


def _path_ok(path: str, token: str) -> bool:
    p = (path or "/").split("?", 1)[0].rstrip("/")
    if not token:
        return True
    return p == f"/tv/{token}"


def make_handler(store: TvSignalStore, token: str = "") -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args: Any) -> None:
            pass

        def _deny(self) -> None:
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if not _path_ok(self.path, token):
                return self._deny()
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            try:
                sig = parse_alert(body)
                store.add(sig)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True, "level": sig.level}).encode())
            except Exception as exc:  # noqa: BLE001
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"ok": False, "error": str(exc)[:120]}).encode())

        def do_GET(self) -> None:  # noqa: N802
            if not _path_ok(self.path, token):
                return self._deny()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps({"ok": True, "signals": len(store.signals)}).encode()
            )

    return Handler


def serve(
    store: TvSignalStore,
    *,
    host: str = "127.0.0.1",
    port: int = 8799,
    token: str = "",
) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), make_handler(store, token))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd