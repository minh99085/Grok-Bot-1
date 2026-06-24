# Risk Skill

## Kill-switch rules (code-enforced)

- Close all positions if drawdown exceeds 5%
- Halt loop if reconciliation invariants fail
- Halt if data feed staleness exceeds configured threshold

## Monitoring cadence

- Pull open positions every 1 minute in isolated worktree
- Log every kill event to STATE.md with timestamp and root cause

## Live gate (closed by design)

Live execution requires BOTH:
1. `walk_forward.validated == True` with deflated Sharpe ≥ threshold on ≥ min OOS trades
2. Explicit human sign-off in `state.json` (`live_signoff.approved`)

No broker live-routing code exists in this repo.