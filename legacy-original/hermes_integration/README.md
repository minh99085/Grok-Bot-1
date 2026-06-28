# Hermes Agent integration

Grok-Bot-1 uses [Hermes Agent](https://github.com/NousResearch/hermes-agent) as the **automation shell** (cron, gateway, skills). The profit-discovery loop engine lives in `loop/` + `grok_bot/`; Hermes schedules and notifies.

## Setup

```bash
# 1. Clone Hermes (if not present)
bash scripts/setup_hermes.sh

# 2. Install Hermes (see hermes-agent README)
cd hermes-agent && curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# 3. Copy Grok-Bot-1 skills into Hermes skills dir
bash scripts/link_hermes_skills.sh

# 4. Register cron jobs
bash scripts/install_hermes_cron.sh
```

## Cron jobs (profit discovery)

| Job | Schedule | Command |
|---|---|---|
| `grok-bot-discovery-cycle` | every 5 min | `python -m grok_bot.main --discover-once` |
| `grok-bot-discovery-report` | every 1 hour | `python -m grok_bot.main --discovery-status` |
| `grok-bot-risk-monitor` | every 1 min | `python -m grok_bot.main --risk-check` |

Long-running discovery: `python -m grok_bot.main --discover-loop`

TradingView webhook (parallel): `python -m grok_bot.main --tradingview-webhook`

## Profit discovery state

- **Mode:** `profit_discovery` (paper-only, no live routing)
- **Rungs:** `observe` → `shadow` → `armed` OR `no_edge_found`
- **Reports:** `reports/discovery_status.md`, `reports/windows.jsonl`
- **State:** `reports/loop_state/STATE.md`