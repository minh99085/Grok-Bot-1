import tempfile
from pathlib import Path

from grok_bot.evidence import EvidenceStore, WindowRecord, promotion_rung
from grok_bot.factory import build_discovery_engine
from loop.state import StateManager


def test_promotion_rung_observe_without_trades():
    promo = promotion_rung([])
    assert promo["rung"] == "observe"
    assert "no_paper_trades" in promo["blockers"]


def test_profit_discovery_engine_scripted_cycle():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        engine = build_discovery_engine(
            scripted=True,
            state_root=root / "state",
            reports_dir=root / "reports",
        )
        status = engine.status()
        assert status["mode"] == "profit_discovery"
        assert status["status"] == "observe"

        engine.loop.run_cycle()
        status2 = engine.status()
        assert status2["windows_processed"] >= 0


def test_discovery_goal_loop_bounded():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        engine = build_discovery_engine(
            scripted=True,
            state_root=root / "state",
            reports_dir=root / "reports",
        )
        engine.config.max_windows = 3
        outcome = engine.run()
        assert outcome.windows_processed <= 3
        assert outcome.stop_reason in ("edge_proven", "budget_exhausted")


def test_evidence_store_append():
    with tempfile.TemporaryDirectory() as tmp:
        store = EvidenceStore(Path(tmp) / "w.jsonl")
        store.append(WindowRecord(0, 1, 0.6, 10.0, "UP", "paper_fill", 1.0))
        assert len(store.records) == 1