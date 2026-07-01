# Technical Data Grades

**Generated:** 2026-07-01T02:02:52.831701+00:00  
**Repo SHA:** `e77473d47972`  
**Ticks:** 719 | **Settled:** 24

## Composite

| Metric | Score | Grade |
|--------|------:|-------|
| **Composite** | **56.5** | **F** |
| Report overall | 44.8 | F |
| Technical runtime | 83.9 | B |

## Report scores (engine)

| Section | Score | Grade |
|---------|------:|-------|
| Trading Performance | 37.2 | F |
| Operation | 76.8 | C+ |
| External Signals | 28.0 | F |

## Technical runtime

_RTDS/oracle health, TV observe-only intake, design manifest compliance, pipeline integrity, gate coupling._

| Component | Score | Weight |
|-----------|------:|-------:|
| rtds_health | 97.0 | 20 |
| tv_intake | 86.7 | 20 |
| design_compliance | 70.0 | 25 |
| trade_pipeline | 100.0 | 20 |
| gate_coupling | 64.1 | 15 |

### Rtds Health (97.0)

| Component | Score | Weight |
|-----------|------:|-------:|
| connected | 100.0 | 35 |
| oracle_fresh | 100.0 | 30 |
| stability | 85.0 | 20 |
| price_feed | 100.0 | 15 |

### Tv Intake (86.7)

| Component | Score | Weight |
|-----------|------:|-------:|
| observe_only | 100.0 | 25 |
| alert_flow | 100.0 | 25 |
| reject_rate | 71.3 | 15 |
| trade_gates_off | 100.0 | 20 |
| mtf_freshness | 40.0 | 15 |

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

### Gate Coupling (64.1)

| Component | Score | Weight |
|-----------|------:|-------:|
| lifecycle_funnel | 33.8 | 25 |
| exec_pass_rate | 81.7 | 25 |
| reject_diversity | 63.8 | 20 |
| cohort_session_load | 100.0 | 15 |
| recent_eval_spread | 50.0 | 15 |

## VPS score history (last entries)

| UTC | Settled | Overall | Trading | Operation | External |
|-----|--------:|--------:|--------:|----------:|---------:|
| 2026-06-30 23:33:06 UTC | 24 | 44.8 | 37.2 | 76.8 | 28.0 |
| 2026-07-01 00:03:06 UTC | 24 | 44.8 | 37.2 | 76.8 | 28.0 |
| 2026-07-01 00:33:08 UTC | 24 | 44.8 | 37.2 | 76.8 | 28.0 |
| 2026-07-01 01:03:22 UTC | 24 | 44.8 | 37.2 | 76.8 | 28.0 |
| 2026-07-01 01:33:37 UTC | 24 | 44.8 | 37.2 | 76.8 | 28.0 |
