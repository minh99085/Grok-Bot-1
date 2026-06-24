# loop/

Operational shell implementing the six pieces and five stages from the Grok-Bot-1 blueprint.

## Six pieces

| Piece | Module |
|---|---|
| Automation | `runner.py` — `@loop`, `@goal`, caps on iterations and wall-clock |
| Skills | `skills/*.md`, `skills.py` |
| State | `state.py` — `STATE.md` + `state.json` |
| Verifier | `verifier.py` — pure-function checker |
| Worktrees | `orchestrator.py`, `scripts/spawn_worktrees.sh` |
| Connectors | `connectors/` — SQLite metrics, TradingView BTCUSDT webhook, Slack/console notifier |

## Five stages

`driver.py` (`DiscoveryLoop`) runs: ingest → signal → verify → execute (paper) → monitor.

## Self-improvement

`self_improve.py` — analyst proposes, pre-check + independent reviewer confirms, lesson appended to skill file. Threshold changes re-validated next cycle.