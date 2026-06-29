# Technical Data Grades

**Generated:** 2026-06-29T20:25:29.219472+00:00  
**Repo SHA:** `7bc7e7f896fb`  
**Ticks:** 7 | **Settled:** 2

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **60.0** | **D** |
| Report overall | 50.1 | F |
| Technical runtime | 83.1 | B |

## Report scores (engine)

| Section | Score | Grade |
|---------|------:|-------|
| Trading Performance | 39.8 | F |
| Operation | 75.4 | C+ |
| External Signals | 45.6 | F |

## Technical runtime

_RTDS/oracle health, TV observe-only intake, design manifest compliance, pipeline integrity, gate coupling._

| Component | Score | Weight |
|-----------|------:|-------:|
| rtds_health | 100.0 | 20 |
| tv_intake | 91.4 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 90.3 | 20 |
| gate_coupling | 61.5 | 15 |

### Rtds Health (100.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 100.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (91.4)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 62.5 | 15 |
| trade_gates_off | 100.0 | 20 |
| mtf_freshness | 80.0 | 15 |

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

### Trade Pipeline (90.3)

| Component | Score | Weight |
|-----------|------:|-------:|
| accounting_integrity | 100.0 | 25 |
| lifecycle | 100.0 | 20 |
| execution_gate | 100.0 | 20 |
| recon_checks | 100.0 | 15 |
| not_halted | 100.0 | 10 |
| uptime_ticks | 3.5 | 10 |

### Gate Coupling (61.5)

| Component | Score | Weight |
|-----------|------:|-------:|
| lifecycle_funnel | 30.0 | 25 |
| exec_pass_rate | 60.0 | 25 |
| reject_diversity | 63.8 | 20 |
| cohort_session_load | 100.0 | 15 |
| recent_eval_spread | 75.0 | 15 |

## VPS score history (last entries)

| UTC | Settled | Overall | Trading | Operation | External |
|-----|--------:|--------:|--------:|----------:|---------:|
| 2026-06-29 18:48:13 UTC | 1 | 36.8 | 21.2 | 59.1 | 45.6 |
| 2026-06-29 19:06:58 UTC | 2 | 36.7 | 20.7 | 59.9 | 45.6 |
| 2026-06-29 19:37:13 UTC | 2 | 36.3 | 19.8 | 59.9 | 45.6 |
| 2026-06-29 19:48:58 UTC | 2 | 50.3 | 39.8 | 76.0 | 45.6 |
| 2026-06-29 20:19:13 UTC | 2 | 50.2 | 39.8 | 75.7 | 45.6 |
