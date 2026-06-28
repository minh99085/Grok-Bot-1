from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookSnapshot:
    best_bid: float
    best_ask: float
    bid_size: float = 100.0
    ask_size: float = 100.0
    ts_ms: int = 0

    @property
    def mid(self) -> float:
        return (self.best_bid + self.best_ask) / 2.0