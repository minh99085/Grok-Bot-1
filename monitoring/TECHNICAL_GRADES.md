# Technical Data Grades

**Generated:** 2026-06-29T00:21:16.609258+00:00  
**Repo SHA:** `b8c9759d179e`  
**Ticks:** 655 | **Settled:** 0

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **69.7** | **D** |
| Report overall | 63.3 | D |
| Technical runtime | 84.7 | B |

## Report scores (engine)

| Section | Score | Grade |
|---------|------:|-------|
| Trading Performance | 66.4 | D |
| Operation | 70.9 | C |
| External Signals | 49.4 | F |

## Technical runtime

_RTDS/oracle health, TV observe-only intake, design manifest compliance, pipeline integrity, gate coupling._

| Component | Score | Weight |
|-----------|------:|-------:|
| rtds_health | 97.0 | 20 |
| tv_intake | 99.4 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 100.0 | 20 |
| gate_coupling | 52.6 | 15 |

### Rtds Health (97.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 85.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (99.4)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 95.7 | 15 |
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
| 2026-06-28 22:16:10 UTC | 0 | 59.1 | 58.9 | 69.4 | 49.4 |
| 2026-06-28 22:46:25 UTC | 0 | 59.9 | 60.3 | 69.7 | 49.4 |
| 2026-06-28 23:15:10 UTC | 0 | 61.4 | 63.1 | 70.1 | 49.4 |
| 2026-06-28 23:45:11 UTC | 0 | 62.1 | 64.3 | 70.4 | 49.4 |
| 2026-06-29 00:15:10 UTC | 0 | 63.3 | 66.4 | 70.8 | 49.4 |
