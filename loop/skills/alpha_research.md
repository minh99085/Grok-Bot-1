# Alpha Research Skill

## Goal

Generate Polymarket signal candidates from ingested market data and **TradingView BTCUSDT** alerts. Propose only — never self-grade. Maker model: **Grok/xAI**.

## Rules

- Sharpe ratio must exceed 1.5 in 3 of the last 5 backtests before arming
- Position size capped at 2% of capital per signal
- Skip signals 48 hours before earnings releases
- Skip momentum signals on FOMC announcement days
- Cap sector exposure at 30%

## Lessons learned

- Predecessor failure: 290 trades, −$76.80, profit factor 0.82, Brier ≈ coin-flip. Observe-only until calibration arms.
- 2026-02-14: Lost 4.2% during earnings week. New rule: skip any signal 48 hours before earnings.