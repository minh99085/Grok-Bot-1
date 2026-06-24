"""CLI entrypoint for Grok-Bot-1."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from loop.driver import DiscoveryLoop
from loop.state import StateManager
from loop.verifier import verify_signal
from grok_bot.safety import LiveTradingDisabledError, submit_order


def _scripted_ingest() -> dict[str, Any]:
    return {"symbol": "btc-updown-5m", "mid": 0.51, "ts": "scripted"}


def _scripted_propose(data: dict[str, Any]) -> dict[str, Any] | None:
    return {
        "name": "directional_observe",
        "symbol": data["symbol"],
        "sharpe": 1.8,
        "max_drawdown": 0.04,
        "newey_west_t": 2.5,
        "oos_years": 2.5,
        "edge": 0.02,
        "notional": 100.0,
    }


def verify() -> int:
    """Offline deterministic checks — no network."""
    checks: dict[str, bool] = {}

    checks["paper_fill_works"] = submit_order({"name": "t"}, paper=True)["paper"] is True
    try:
        submit_order({"name": "t"}, paper=False)
        checks["live_blocked"] = False
    except LiveTradingDisabledError:
        checks["live_blocked"] = True

    good = verify_signal(
        {"sharpe": 2.0, "max_drawdown": 0.05, "newey_west_t": 2.5, "oos_years": 2.5}
    )
    bad = verify_signal({"sharpe": 0.5, "max_drawdown": 0.20, "newey_west_t": 0.5, "oos_years": 0.5})
    checks["verifier_passes_good"] = good.passed
    checks["verifier_rejects_bad"] = not bad.passed

    with tempfile.TemporaryDirectory() as tmp:
        mgr = StateManager(Path(tmp))
        loop = DiscoveryLoop(state_mgr=mgr, ingest=_scripted_ingest, propose=_scripted_propose)
        results = loop.run_cycle()
        state = mgr.read()
        checks["cycle_ran"] = len(results) >= 4
        checks["state_persisted"] = state.windows_processed == 1

    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


def discover_once() -> int:
    mgr = StateManager()
    loop = DiscoveryLoop(state_mgr=mgr, ingest=_scripted_ingest, propose=_scripted_propose)
    results = loop.run_cycle()
    print(json.dumps({"results": [r.__dict__ for r in results], "status": loop.discovery_status()}, indent=2, default=str))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="grok-bot")
    parser.add_argument("--verify", action="store_true", help="offline safety + loop checks")
    parser.add_argument("--discover-once", action="store_true", help="run one paper discovery cycle")
    args = parser.parse_args()

    if args.verify:
        return verify()
    if args.discover_once:
        return discover_once()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())