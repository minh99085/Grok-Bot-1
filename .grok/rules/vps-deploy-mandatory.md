# VPS deploy — mandatory sequence (operator rule)

**Non-negotiable:** After every push to `origin/main`, sync the VPS to that SHA, remove orphan containers, and rebuild — unless `state.json` is in `hands_off`.

## Required sequence

1. **Repo ↔ `origin/main` aligned**
   - Local `HEAD` must equal `origin/main` before deploy.
   - If behind: `git pull --ff-only origin main`. If ahead: `git push origin main` first.

2. **VPS ↔ `origin/main` aligned**
   - Run `.\scripts\sync-vps.ps1` from `C:\Users\tieut\Grok-Bot-1`.
   - VPS `/opt/Grok-Bot-1` HEAD must match `origin/main` after bundle sync.

3. **Orphan cleanup + full rebuild (always)**
   - `python3 scripts/apply-loop-arch-env.py`
   - `python3 scripts/pulse-babysit/validate-frozen-lock.py`
   - `docker compose down --remove-orphans`
   - `docker compose build`
   - `docker compose up -d --force-recreate --remove-orphans`

4. **Verify**
   - `.\scripts\verify-sync.ps1` — VPS HEAD == `origin/main`; containers healthy.

## Never

- Push to `main` and stop without VPS deploy.
- `-SkipRebuild` unless the operator explicitly requests code-only sync in the current message.
- `docker compose restart` or single-service recreate instead of full down → build → up.
- Deploy Bot 1 changes to Bot 2 VPS (or vice versa).

## Bot 1 targets

| Item | Value |
|------|-------|
| Repo | `https://github.com/minh99085/Grok-Bot-1` |
| VPS | `linuxuser@45.32.227.242` |
| Path | `/opt/Grok-Bot-1` |
| Script | `.\scripts\sync-vps.ps1` |

`sync-vps.ps1` implements steps 2–3; run `verify-sync.ps1` after.