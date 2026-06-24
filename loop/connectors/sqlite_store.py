"""Read-only / write-metrics results store."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class SqliteStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cycle_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def append_cycle(self, ts: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT INTO cycle_log (ts, payload) VALUES (?, ?)",
                (ts, json.dumps(payload)),
            )