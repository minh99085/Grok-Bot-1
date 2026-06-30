# Grok-Bot-1

**Bot 1** — standalone BTC pulse paper bot (Hermes trading engine).

| | Bot 1 |
|---|-------|
| **Strategy** | `arb_first_perfect_wr_v1` (sweet-spot 0.47–0.55 entry band) |
| **VPS** | `45.32.227.242` (`ssh bot1`) |
| **Path** | `/opt/Grok-Bot-1` |
| **Deploy** | `.\scripts\sync-vps.ps1` |

Original loop-engine blueprint and `grok_bot` daemon live under `legacy-original/`.

## Quick start (operator)

```powershell
cd C:\Users\tieut\Grok-Bot-1
.\scripts\sync-vps.ps1
```

Profile: `scripts/bot-profile.json`