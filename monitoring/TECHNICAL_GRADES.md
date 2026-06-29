# Technical Data Grades

**Generated:** 2026-06-29T11:34:41.455241+00:00  
**Repo SHA:** `e7b1c4ec0592`  
**Ticks:** 1215 | **Settled:** 0

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **70.0** | **C** |
| Report overall | 65.2 | D |
| Technical runtime | 81.3 | B |

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
| rtds_health | 94.0 | 20 |
| tv_intake | 85.7 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 100.0 | 20 |
| gate_coupling | 52.6 | 15 |

### Rtds Health (94.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 70.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (85.7)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 44.7 | 15 |
| trade_gates_off | 100.0 | 20 |
| mtf_freshness | 60.0 | 15 |

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

### Trade Pipeline (100.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| accounting_integrity | 100.0 | 25 |
| lifecycle | 100.0 | 20 |
| execution_gate | 100.0 | 20 |
| recon_checks | 100.0 | 15 |
| not_halted | 100.0 | 10 |
| uptime_ticks | 100.0 | 10 |

### Gate Coupling (52.6)

| Component | Score | Weight |
|-----------|------:|-------:|
| lifecycle_funnel | 30.0 | 25 |
| exec_pass_rate | 40.0 | 25 |
| reject_diversity | 63.2 | 20 |
| cohort_session_load | 100.0 | 15 |
| recent_eval_spread | 50.0 | 15 |

## VPS score history (last entries)

| UTC | Settled | Overall | Trading | Operation | External |
|-----|--------:|--------:|--------:|----------:|---------:|
| 2026-06-29 10:21:40 UTC | 0 | 65.2 | 70.0 | 71.5 | 49.4 |
| 2026-06-29 10:51:41 UTC | 0 | 64.6 | 68.8 | 71.5 | 49.4 |
| 2026-06-29 11:01:55 UTC | 0 | 51.2 | 49.5 | 56.5 | 49.4 |
| 2026-06-29 11:17:55 UTC | 0 | 44.0 | 35.0 | 56.5 | 49.4 |
| 2026-06-29 11:32:55 UTC | 0 | 65.2 | 70.0 | 71.5 | 49.4 |
