---
name: grok-bot-profit-discovery
description: Operate Grok-Bot-1 profit discovery loop on Polymarket BTC 5m windows
---

# Grok-Bot-1 Profit Discovery

## Mission

Discover whether **real paper-trading edge** exists on Polymarket `btc-updown-5m-*` — not deploy live capital.

## State

- Mode: `profit_discovery`
- Rungs: `observe` → `shadow` → `armed` | `no_edge_found`
- Read `reports/loop_state/STATE.md` and `reports/discovery_status.md` every cycle

## Feed stack (leading before Chainlink)

1. Binance BTCUSDT
2. Coinbase BTC-USD
3. TradingView BTCUSDT alerts
4. Chainlink BTC/USD — settlement truth only

## LLM roles

- **Maker:** Grok/xAI (`XAI_API_KEY`)
- **Checker:** Claude (`ANTHROPIC_API_KEY`)

## Commands

```bash
python -m grok_bot.main --discover-loop
python -m grok_bot.main --discovery-status
python -m grok_bot.main --tradingview-webhook
python -m grok_bot.main --verify
```

## Rules

- Paper-only forever unless human sign-off in `state.json` AND armed rung proven
- Never self-grade signals — numeric verifier + Claude checker
- Log every loss to `loop/skills/alpha_research.md`