import json
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from grok_bot.config import BotConfig
from grok_bot.dashboard import build_snapshot, serve_dashboard
from grok_bot.evidence import EvidenceStore, WindowRecord
from loop.state import StateManager


def _seed_reports(root: Path) -> None:
    state_mgr = StateManager(root / "loop_state")
    state = state_mgr.read()
    state.windows_processed = 3
    state.last_verdict = "paper_fill"
    state_mgr.write(state)

    evidence = EvidenceStore(root / "windows.jsonl")
    for i in range(1, 4):
        evidence.append(
            WindowRecord(
                window_id=i,
                ts_ms=1_700_000_000_000 + i * 300_000,
                p_up=0.55,
                edge_bps=5.0,
                implied_direction="UP",
                action="paper_fill",
                simulated_pnl=0.12,
                leading_confidence=0.6,
            )
        )

    (root / "discovery_status.json").write_text(
        json.dumps({"headline": "test headline", "mode": "profit_discovery"}),
        encoding="utf-8",
    )


def test_build_snapshot():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _seed_reports(root)
        snap = build_snapshot(reports_dir=root, cfg=BotConfig())
        assert snap["windows_processed"] == 3
        assert snap["portfolio"]["trades"] == 3
        assert snap["headline"] == "test headline"
        assert len(snap["recent_windows"]) == 3


def test_dashboard_http():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _seed_reports(root)
        cfg = BotConfig(dashboard_host="127.0.0.1", dashboard_port=18880, dashboard_token="")
        serve_dashboard(cfg, reports_dir=root)
        time.sleep(0.2)

        def fetch(path: str) -> bytes:
            return urllib.request.urlopen(f"http://127.0.0.1:18880{path}", timeout=3).read()

        html = fetch("/").decode()
        assert "Grok-Bot-1" in html
        assert "test headline" in html

        data = json.loads(fetch("/api/status"))
        assert data["windows_processed"] == 3