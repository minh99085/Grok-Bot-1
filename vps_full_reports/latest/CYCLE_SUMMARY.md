# Bot cycle summary (plain English)

_Updated: 2026-07-01 02:02 UTC_

## Last cycle

| | |
|---|---|
| **Cycle #** | 1 |
| **Checked at** | 2026-06-30 03:35 UTC |
| **Result** | **issues_fixed_overnight_soak** |
| **What it means** | Result: issues_fixed_overnight_soak |
| **Next check after** | 2026-06-30 11:45 UTC |

**Issues flagged:** strategy_halted

**Fixes applied:**

- mid_exit_convergence paper lane (60s horizon)
- wire dep_arb stop halt before new executes
- max_entry_vwap 0.52 + PULSE_MAX_PRICE 0.52
- stop guard recovery when mid_convergence n>=5 rate>=0.5
- evaluate-cycle strategy_halted names correct strategy

## How the bot is doing now

| | |
|---|---|
| **Mode** | Paper only (fake money) |
| **Started with** | $500.00 |
| **Total now** | $93.49 (-81.3% return) |
| **Arb profit** | $0.00 (0 trades) |
| **Directional profit** | $0.07 |
| **Win rate** | 50.0% (24 settled trades) |
| **UP win rate** | — |
| **DOWN win rate** | 50.0% |
| **Bot stopped?** | No — bot is running |
| **Overall grade** | — (—/100) |

### 5m vs 15m (recent)

| Market | Trades | Win rate | PnL |
|--------|--------|----------|-----|
| **15m** | 24 | 50.0% | $0.07 |
| **5m** | — | — | — |

### TradingView (INDEX:BTCUSD)

- Alerts received: **2071**
- 5-chart trend: **none** (—/3 fresh)

## Quick verdict

**Good:** Bot is running normally.

---

_Auto-generated after each `/pulse-babysit` cycle. Full report: `report.md` / `report.docx` in this folder._
