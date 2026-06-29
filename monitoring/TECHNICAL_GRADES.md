# Technical Data Grades

**Generated:** 2026-06-29T11:43:52.058221+00:00  
**Repo SHA:** `c5f841e8ad34`  
**Ticks:** 5 | **Settled:** 0

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **70.2** | **C** |
| Report overall | 65.2 | D |
| Technical runtime | 82.0 | B |

## Report scores (engine)

| Section | Score | Grade |
|---------|------:|-------|
| Trading Performance | 70.0 | C |
| Operation | 71.5 | C |
| External Signals | 49.4 | F |

## Technical runtime

_RTDS/oracle health, TV observe-only intake, design manifest compliance, pipeline integrity, gate coupling._

| Component | Score | Weight |
|-----------|------:|-------:|
| rtds_health | 100.0 | 20 |
| tv_intake | 91.8 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 90.2 | 20 |
| gate_coupling | 54.1 | 15 |

### Rtds Health (100.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 100.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (91.8)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 45.1 | 15 |
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

### Trade Pipeline (90.2)

| Component | Score | Weight |
|-----------|------:|-------:|
| accounting_integrity | 100.0 | 25 |
| lifecycle | 100.0 | 20 |
| execution_gate | 100.0 | 20 |
| recon_checks | 100.0 | 15 |
| not_halted | 100.0 | 10 |
| uptime_ticks | 2.5 | 10 |

### Gate Coupling (54.1)

| Component | Score | Weight |
|-----------|------:|-------:|
| lifecycle_funnel | 30.0 | 25 |
| exec_pass_rate | 40.0 | 25 |
| reject_diversity | 63.2 | 20 |
| cohort_session_load | 100.0 | 15 |
| recent_eval_spread | 60.0 | 15 |

## VPS score history (last entries)

| UTC | Settled | Overall | Trading | Operation | External |
|-----|--------:|--------:|--------:|----------:|---------:|
| 2026-06-29 10:21:40 UTC | 0 | 65.2 | 70.0 | 71.5 | 49.4 |
| 2026-06-29 10:51:41 UTC | 0 | 64.6 | 68.8 | 71.5 | 49.4 |
| 2026-06-29 11:01:55 UTC | 0 | 51.2 | 49.5 | 56.5 | 49.4 |
| 2026-06-29 11:17:55 UTC | 0 | 44.0 | 35.0 | 56.5 | 49.4 |
| 2026-06-29 11:32:55 UTC | 0 | 65.2 | 70.0 | 71.5 | 49.4 |
