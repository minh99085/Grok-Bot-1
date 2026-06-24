import tempfile
from pathlib import Path

from loop.driver import DiscoveryLoop
from loop.state import StateManager


def test_end_to_end_cycle_promotes_to_shadow():
    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))

        def ingest():
            return {"symbol": "btc-updown-5m"}

        def propose(data):
            return {
                "name": "test",
                "symbol": data["symbol"],
                "sharpe": 1.9,
                "max_drawdown": 0.03,
                "newey_west_t": 2.2,
                "oos_years": 2.1,
                "edge": 0.01,
                "notional": 100,
            }

        loop = DiscoveryLoop(state_mgr=mgr, ingest=ingest, propose=propose)
        results = loop.run_cycle()
        state = mgr.read()

        assert any(r.stage == "execute" and r.ok for r in results)
        assert state.windows_processed == 1
        assert state.current_rung == "shadow"
        assert mgr.json_path.exists()
        assert mgr.md_path.exists()