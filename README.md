# Grok-Bot-1

**Bot 1** — BTC pulse paper bot (Hermes trading engine), paired A/B test against [Grok-Bot-2](https://github.com/minh99085/Grok-Bot-2).

| | Bot 1 | Bot 2 |
|---|-------|-------|
| **Strategy** | `sweet_spot_only_v1` (0.47–0.55 entry band) | `real_money_discipline` (wider band) |
| **VPS** | `45.32.227.242` (`ssh bot1`) | `45.32.224.147` (`ssh bot2`) |
| **Path** | `/opt/Grok-Bot-1` | `/opt/Grok-Bot-2` |
| **Deploy** | `.\scripts\sync-vps.ps1` | same in Grok-Bot-2 repo |

Original loop-engine blueprint and `grok_bot` daemon live under `legacy-original/`.

## Quick start (operator)

```powershell
cd C:\Users\tieut\Grok-Bot-1
.\scripts\sync-vps.ps1
```

Profile: `scripts/bot-profile.json`