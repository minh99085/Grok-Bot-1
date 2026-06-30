# Technical Data Grades

**Generated:** 2026-06-30T03:22:57.818262+00:00  
**Repo SHA:** `df764b0f6c46`  
**Ticks:** 715 | **Settled:** 9

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **51.3** | **F** |
| Report overall | 37.7 | F |
| Technical runtime | 83.0 | B |

## Report scores (engine)

| Section | Score | Grade |
|---------|------:|-------|
| Trading Performance | 30.7 | F |
| Operation | 61.5 | D |
| External Signals | 28.0 | F |

## Technical runtime

_RTDS/oracle health, TV observe-only intake, design manifest compliance, pipeline integrity, gate coupling._

| Component | Score | Weight |
|-----------|------:|-------:|
| rtds_health | 97.0 | 20 |
| tv_intake | 95.5 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 90.0 | 20 |
| gate_coupling | 60.3 | 15 |

### Rtds Health (97.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 85.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (95.5)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 70.2 | 15 |
| trade_gates_off | 100.0 | 20 |
| mtf_freshness | 100.0 | 15 |

### Design Compliance (70.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| series_15m | 100.0 | 15 |
| green_path | 100.0 | 10 |
| paper_only | 100.0 | 10 |
| grok_shadow | 100.0 | 5 |
| tick_seconds | 100.0 | 10 |
| max_price | 50.0 | 10 |
| min_edge | 50.0 | 5 |
| min_reward_risk | 50.0 | 5 |
| cohort_relaxed | 100.0 | 10 |
| tv_trade_gates_off | 0.0 | 20 |

### Trade Pipeline (90.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| accounting_integrity | 100.0 | 25 |
| lifecycle | 100.0 | 20 |
| execution_gate | 100.0 | 20 |
| recon_checks | 100.0 | 15 |
| not_halted | 0.0 | 10 |
| uptime_ticks | 100.0 | 10 |

### Gate Coupling (60.3)

| Component | Score | Weight |
|-----------|------:|-------:|
| lifecycle_funnel | 31.4 | 25 |
| exec_pass_rate | 77.2 | 25 |
| reject_diversity | 63.8 | 20 |
| cohort_session_load | 61.0 | 15 |
| recent_eval_spread | 75.0 | 15 |

## VPS score history (last entries)

| UTC | Settled | Overall | Trading | Operation | External |
|-----|--------:|--------:|--------:|----------:|---------:|
| 2026-06-30 01:18:15 UTC | 8 | 42.0 | 39.3 | 61.6 | 28.0 |
| 2026-06-30 01:48:30 UTC | 8 | 42.0 | 39.3 | 61.6 | 28.0 |
| 2026-06-30 02:18:44 UTC | 8 | 42.0 | 39.3 | 61.6 | 28.0 |
| 2026-06-30 02:32:46 UTC | 9 | 37.8 | 30.7 | 61.7 | 28.0 |
| 2026-06-30 03:03:00 UTC | 9 | 37.8 | 30.7 | 61.8 | 28.0 |
