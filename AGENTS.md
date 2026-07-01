# Grok-Bot-1 — project rules

## Quant team mandate (ALWAYS follow)

Operate as a **quant research + engineer + trader** team targeting **~80% WR** on selective entries.
Each cycle: read live performance → hypothesize from market + bot data → implement minimal gate/strategy
changes → measure on 15-min soak. See `.grok/rules/quant-team.md`.

## Roan / Bregman architecture (Phase 0+)

5m brain, 15m hands — `docs/roan-bregman-architecture.md`. Promotion gates:
`scripts/pulse-babysit/roan-bregman-promotion-scorecard.json`.
**Promotion gate LIFTED 2026-07-01 (operator "remove all locks"):** `PULSE_DEPENDENCY_ARB_EXECUTE`
and `PULSE_BREGMAN_TRADE_AUTHORITY` are now ON; the loop learns/grades their edge from live outcomes.
Still **PAPER ONLY**.

## Soak / learning collection lock (OPERATOR MANDATE — LIFTED 2026-07-01)

**LIFTED 2026-07-01 (operator "remove all locks; make the loop learn and adjust").** The soak/learning
freeze no longer applies — the closed loop governs gates/sizing/authority from live evidence. Still run
`validate-frozen-lock.py` before deploy (now enforces only the retained invariants + API keys). See
`.grok/rules/soak-learning-lock.md` and `scripts/pulse-babysit/frozen-env-keys.json`
(`retained_invariants_never_lifted`).

## TradingView observe-only lock (OPERATOR MANDATE — LIFTED 2026-07-01)

**LIFTED 2026-07-01 (operator "remove all locks").** No longer enforced. NOTE: TV trade gates are
still set to `0` (OFF) in `apply-loop-arch-env.py` on purpose — TV is negative-alpha and currently
stale, so enabling gates would only block trades and starve the learners. TV intake stays on as
observe features; the loop may adjust TV usage from evidence. Detail:
`.grok/rules/tv-observe-only-lock.md`.

## Repository scope (ALWAYS follow)

- **Canonical repo:** `https://github.com/minh99085/Grok-Bot-1` — the **only** GitHub repository for code, commits, pushes, reports, and deploys.
- **Do not** clone, commit, or push to `hermes-agent-cursor` or any other repo unless the operator explicitly overrides this in the current message.
- **Local workspace:** prefer `C:\Users\tieut\Grok-Bot-1` when working from this machine.
- **Default branch:** `main`.
- **VPS deploy (MANDATORY after every push to `main`):** See `.grok/rules/vps-deploy-mandatory.md`.
  **Always push every change to `main` AND deploy to the VPS** (2026-07-01 operator rule) — don't
  stop at a feature branch/PR.
  **Always remove orphans and rebuild after VPS sync** — `.\scripts\sync-vps.ps1` (default rebuild ON:
  `down --remove-orphans` → `build` → `up -d --force-recreate --remove-orphans`) → `verify-sync.ps1`.
  **Never** `-SkipRebuild` unless operator explicitly requests code-only sync in the current message.

## Project layout

- Trading bot plugin: `hermes-agent-main/plugins/hermes-trading-engine/`
- Full VPS reports: **only** `vps_full_reports/latest/` on `main` — see `.grok/rules/vps-full-report.md`.
  Engine must generate a **real full report** (`FULL_REPORT.md` + provenance bundle). On every pull:
  wipe `latest/`, pull fresh from VPS, remove stale tracked files, commit + push to `origin/main`.
  Canonical URL: https://github.com/minh99085/Grok-Bot-1/tree/main/vps_full_reports/latest
- Design townhall: `Design Townhall` (repo root)
- Operator guide for the pulse engine: `hermes-agent-main/plugins/hermes-trading-engine/AGENTS.md`
- Autonomous closed loop: `/pulse-babysit cycle` or `.\scripts\pulse-babysit\install-scheduled-task.ps1` (15m soak default; see `.grok/skills/pulse-babysit/SKILL.md`)