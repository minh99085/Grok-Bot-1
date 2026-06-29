---
name: pulse-babysit
description: >-
  Autonomous BTC pulse bot closed loop: soak on VPS after deploy, pull reports,
  score trading performance, diagnose issues, fix code, commit/push main, sync-vps
  with orphan cleanup and rebuild, repeat. Use when the user wants hands-off bot
  iteration, autonomous improvement, closed-loop ops, or runs /pulse-babysit.
argument-hint: "cycle | force-eval | status | deploy | soak <minutes>"
---

# Pulse Babysit (closed loop)

You operate the **Grok-Bot-1** paper pulse bot without asking the operator for permission
between cycles. Execute tools yourself. Paper-only — never enable live trading.

**Team identity:** quant research + engineer + trader. **`real_money_discipline` mode** —
treat paper PnL as real capital; fix WR/PF/bleed, not just trade rate. Read
`.grok/rules/real-money-discipline.md`, `.grok/rules/self-improve-loop.md`,
`.grok/rules/soak-learning-lock.md`, `.grok/rules/quant-team.md`, and
**`.grok/rules/hands-off-untouchable.md`** (profitable-bot lock).

## Repo anchors

| Item | Path |
|------|------|
| Workspace | `C:\Users\tieut\Grok-Bot-1` |
| Plugin | `hermes-agent-main/plugins/hermes-trading-engine` |
| Deploy | `.\scripts\sync-vps.ps1` (always orphan cleanup + rebuild) |
| VPS | `root@45.32.227.242` `/opt/Grok-Bot-1` |
| Dashboard | `http://45.32.227.242/` |
| State | `scripts/pulse-babysit/state.json` |

## Commands

| Command | Behavior |
|---------|----------|
| `cycle` | Default loop iteration (respects soak timer) |
| `force-eval` | Pull + evaluate now; skip soak wait |
| `status` | Print state + last evaluation summary |
| `deploy` | `git push origin main` + full VPS deploy (sync-vps + env + force-recreate training) |
| `soak <minutes>` | Set soak duration (default **240 min / 4h** in learning_collection) via `set-soak.ps1` |

If no argument: run `cycle`.

## State machine

```
DEPLOY → SOAK (60m real-money default) → PULL → EVALUATE → (issues?) → FIX → COMMIT → DEPLOY → …
```

1. Read `scripts/pulse-babysit/state.json`.
2. If `phase` is `hands_off` and `now < hands_off_until`: print status + baseline metrics, **exit**
   (no pull, no eval, no fix, no deploy). Respect `.grok/rules/hands-off-untouchable.md`.
3. If `phase` is `soak` and `now < soak_until`: run `status`, exit (do not fix).
4. Run `python scripts/pulse-babysit/scan-health.py` — full runtime checklist (Grok/verifier/loops/stop).
   Run `python scripts/pulse-babysit/validate-frozen-lock.py` — manifest drift (P0 authority keys).
5. Run `.\scripts\pulse-babysit\pull-vps-artifacts.ps1` — **wipes** `vps_full_reports/latest/`,
   pulls live VPS artifacts (requires **`FULL_REPORT.md`** — real full report from engine), then
   **always commits + pushes** only that fresh snapshot to `origin/main` (removes stale tracked
   files). See `.grok/rules/vps-full-report.md`. Use `-SkipPush` only for local debugging.
6. Run `python scripts/pulse-babysit/evaluate-cycle.py` — parse JSON stdout.
7. **WR auto-tune (mandatory in `real_money_discipline`):** if eval has **no** `trade_starvation` /
   `trade_starvation_streak`, run:
   `python scripts/pulse-babysit/apply-wr-tune.py --eval-json '<eval stdout>' --apply`
   when `band_issues` is non-empty or `win_rate_below_target` / `cheap_down_bleed` /
   `expensive_down_bleed` appear. This patches `apply-loop-arch-env.py` + `frozen-env-keys.json`
   deterministically (never lowers `PULSE_MIN_ENTRY_PRICE` below **0.45**). Skip when starvation P0.
8. If `verdict` is `healthy`: append history, set `phase=soak`, `soak_until=now+soak_hours`, done.
9. If `verdict` is `issues`: pick **at most 2** highest-severity issues; fix in plugin code **or**
   accept WR tune from step 7 as a fix (counts toward the 2-fix cap).
10. Run targeted tests under `hermes-agent-main/plugins/hermes-trading-engine/tests/` and
    `python -m pytest scripts/pulse-babysit/test_price_band_analysis.py -q` when WR tune changed.
11. Commit with clear message; `git push origin main`.
12. **MANDATORY VPS deploy** (never skip after any push to `main` — unless `hands_off`):
    - See `.grok/rules/vps-deploy-mandatory.md`
    - `.\scripts\sync-vps.ps1` — sync `origin/main` → VPS, apply env, validate frozen lock,
      `down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`, then verify
13. Update state: `phase=soak`, `deployed_at`, `soak_until`, `last_fixes`, increment `cycle`.

## Env coupling (mandatory memory)

Read `scripts/pulse-babysit/env-coupling.md` before any gate/TTC env change.

**Rule:** with baseline cohort + TV context gate both on,
`PULSE_TV_CONTEXT_MAX_TTC_S` must exceed the scaled cohort band on every series in
`PULSE_SERIES_SLUGS` (dual 5m+15m → use **900**, never **180** or **120**).

- Status field: `config_coupling.configured_ok` / `effective_s` / `fix_hint`
- `scan-health.py` flags `gate_coupling_misconfigured` (P0) if `.env` is unsafe
- Engine auto-clamps at runtime but `.env` must still be fixed
- TradingView: **INDEX:BTCUSD** — 2m/3m/4m chart alerts (observe-only); see `tradingview/README.md`
- **Soak/learning lock:** `.grok/rules/soak-learning-lock.md` + `frozen-env-keys.json` — frozen authority
  chain + relaxed quant params; tunable bounds only.
- **TV observe-only lock (operator mandate):** `.grok/rules/tv-observe-only-lock.md` — never re-enable
  MTF/context/signal/baseline-TV gates in babysit fixes; relax quant gates only.

## Evaluation rules (do not override without evidence)

The script flags issues. You may fix only what the report supports:

- **`trade_starvation` / `trade_starvation_streak` (P0)** → settled flat for **2** evals or no fills
  for ≥**3h** (real-money mode). **Relax quant gates** first — never TV trade gates. **Do not tighten**
  WR/PF in the same cycle when starvation is present.
- **`win_rate_below_target` / `profit_factor_low` (P1 — act in real_money_discipline)** → run
  `apply-wr-tune.py --apply` first (price-band evidence); then tighten reward/risk if still below target.
- **`cheap_down_bleed` / `expensive_down_bleed` / `sweet_spot_underuse`** → `apply-wr-tune.py --apply`
  (deterministic; see `wr-tune-policy.json`). Never lower `min_entry_price` below **0.45**.
- `up_side_bleed` → strengthen DOWN-only + quant restrictors (not TV gates)
- `mtf_starved` → TV webhook health only (observe-only); **do not** enable MTF require/side-align
- `reconciliation_broken` → bug fix immediately (P0)
- `verifier_disabled` / `grok_not_follow` → run `validate-vps-env.py` on VPS; fix `.env`; recreate `hermes-training`
- `strategy_halted` → stop_conditions (Wilson/PF/DD); adjust `PULSE_STOP_MIN_SAMPLES` or performance
- `tv_feed_unhealthy` → webhook/secret/symbol (ops)
- `learning_hurts` → learning weight / bench veto

**Never** in autopilot: enable live trading, disable execution gate, re-enable any TV trade gate
(MTF/context/signal/baseline-TV), set exploration > 0 on TV gates, or large refactors.

## Soak duration

| Situation | Duration |
|-----------|----------|
| Real-money discipline (default) | **60 min (1h)** — no deploy/fixes during soak |
| Learning collection (legacy) | **240 min (4h)** |
| Operator override | `.\scripts\pulse-babysit\set-soak.ps1 -Minutes N` |

## Todo scaffold (each cycle)

- `pb:pull` — artifacts on disk
- `pb:eval` — evaluate-cycle.py run
- `pb:fix` — code change (skip if healthy)
- `pb:deploy` — push + sync-rebuild
- `pb:soak` — timer set

## Autonomous scheduling (operator setup)

**Option A — Grok TUI (session open):**
```
/loop 15m /pulse-babysit cycle
/always-approve
```

**Option B — Windows Task Scheduler (hands-off):**
```
.\scripts\pulse-babysit\install-scheduled-task.ps1 -IntervalHours 1
```

**Option C — One-shot headless:**
```
grok -p "/pulse-babysit cycle" --yolo --cwd C:\Users\tieut\Grok-Bot-1 --max-turns 40
```

## Report outputs (mandatory)

**Canonical publish location (only):**
https://github.com/minh99085/Grok-Bot-1/tree/main/vps_full_reports/latest

Read `.grok/rules/vps-full-report.md` before any report pull/push.

- VPS engine must generate a **real full report** every tick (`FULL_REPORT.md` + provenance bundle).
- Pull **wipes** `vps_full_reports/latest/` first — no stale local files.
- Push **removes** stale tracked files in `latest/` on `main`, then commits only the fresh snapshot.
- Required: `FULL_REPORT.md`, `report.docx`, status/ledger JSON, plus `CYCLE_SUMMARY.md`
  (from `write-cycle-summary.py` after pull + evaluate).
- Automatic: `pull-vps-artifacts.ps1` → `push-report-to-main.ps1`.
- Standalone push: `.\scripts\pulse-babysit\push-report-to-main.ps1`.

## Completion message

End with: cycle number, verdict, soak_until (UTC), fixes applied (or "none"), VPS SHA.