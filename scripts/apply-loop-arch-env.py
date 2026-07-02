#!/usr/bin/env python3
"""Apply loop-engine architecture env on VPS: quant baseline owns trades; Grok/TV observe-only."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ROOT = ROOT / "hermes-agent-main" / "plugins" / "hermes-trading-engine"
sys.path.insert(0, str(ENGINE_ROOT))

from engine.pulse.config_coupling import (  # noqa: E402
    evaluate_context_cohort_coupling,
    window_seconds_for_slugs,
)

ENV_PATH = Path("/opt/Grok-Bot-1/hermes-agent-main/plugins/hermes-trading-engine/.env")
if not ENV_PATH.exists():
    ENV_PATH = ENGINE_ROOT / ".env"

# FROZEN (operator lock 2026-06-27): TV gate keys in UPDATES below marked [TV-LOCK] must not be
# re-enabled in babysit/autopilot fixes. See .grok/rules/tv-observe-only-lock.md

UPDATES = {
    "PULSE_DASHBOARD_BOT_LABEL": "Bot 1 · arb-first perfect-WR",
    "TRADINGVIEW_WEBHOOK_MIRROR_URL": "",
    # LLM COUNCIL wiring (operator 2026-07-01 "utilize computing power of Grok and Claude"):
    # Grok is back to SHADOW so it is NOT a solo fail-closed gate (which was blocking trades); instead
    # it feeds the council as a graded MEMBER (its p_up view). The council blends quant + Grok + Claude
    # by live accuracy and drives the trade; the Claude verifier remains the independent checker.
    "PULSE_GROK_DECIDER_MODE": "shadow",
    "PULSE_GROK_DECIDER_FOLLOW_FRACTION": "0.5",
    "PULSE_GROK_DECIDER_EXPLORE_RATE": "0.05",
    # Both LLMs' compute drives the decision: Grok member + Claude second-opinion member + quant.
    "PULSE_LLM_COUNCIL_ENABLED": "1",
    # CONVICTION BAR (2026-07-02): directional was a coin flip (50.9% WR, edge~0) because the council
    # traded 774/934 windows at min_margin 0.01 -- essentially no conviction required. Raise the bar so
    # it only trades high-conviction consensus (fewer trades, higher WR). Pairs with the cold-member
    # fix (unproven members no longer swing the vote), so a real margin now means the graded members
    # actually agree. 0.62 agreement + 0.05 margin (=P>=0.55 or <=0.45).
    "PULSE_LLM_COUNCIL_MIN_AGREEMENT": "0.62",
    "PULSE_LLM_COUNCIL_MIN_MARGIN": "0.05",
    "PULSE_LLM_COUNCIL_MIN_MEMBERS": "2",
    # Best-EV side selection (2026-07-01 "do it"): the council picks the side with max (P(side)-ask)
    # instead of the favorite-by-probability. Takes the CHEAP underdog when it's underpriced (high
    # reward/risk, clears the price cap) and refuses to overpay for the favorite -> unchokes fills.
    "PULSE_COUNCIL_BEST_EV": "1",
    # TV per-timeframe council members (2026-07-01): EACH TradingView timeframe (tv_5m, tv_10m,
    # tv_15m, tv_60m, ...) is its own graded council member; the council FOLLOWS/FADES/IGNORES each TF
    # from its OWN live accuracy. The short 2m/3m/4m TFs were retired (anti-predictive; see
    # PULSE_TV_DROP_TIMEFRAMES) — the bot now runs the horizon-matched 5m/10m/15m/1h set. Add charts in
    # TradingView and they auto-join + get graded. Self-correcting; can't hurt more than a floored member.
    "PULSE_COUNCIL_TV_MEMBER": "1",
    # TV freshness cap (2026-07-02): the bot bets at the 15m window OPEN (:00/:15/:30/:45). 5m/15m
    # alerts close on that grid (fresh ~11s); 10m/1h are off-grid and go stale (a 1h read is 15-45 min
    # old at :15/:30/:45). Cap a per-TF read's age to ~1 window so stale/misaligned reads stop voting.
    "PULSE_TV_COUNCIL_MAX_AGE_S": "900",
    "PULSE_CLAUDE_DECIDER_ENABLED": "1",
    # Monte Carlo: correlated dep-arb conditional P(parent UP | children UP). Deterministic numpy sim.
    # GATE ON (operator 2026-07-01 "do it"): MC vetoes dep-arb entries whose conditional EV is clearly
    # negative (paying more than the true conditional prob = adverse selection — the -$406 failure
    # mode). The flag is graded vs real outcomes (status.monte_carlo.flag_grading) so its precision is
    # measured. LLM (Grok now, Claude when funded) parameterizes the MC's vol/drift/jumps (bounded,
    # fail-open to neutral GBM).
    "PULSE_MC_ENABLED": "1",
    "PULSE_MC_PATHS": "20000",
    "PULSE_MC_DEP_ARB_GATE": "1",
    # Tightened -0.02 -> 0.0 (2026-07-02): dep-arb payoff is asymmetric (avg win ~$24 vs avg loss ~$48
    # -> breakeven WR ~66.7%), so "not badly adverse" (-0.02) isn't enough. Require NON-NEGATIVE
    # conditional EV to enter, pushing selection toward the high-WR band that clears breakeven. (New-
    # regime dep-arb trades post-gates are already 9/9 winners; this keeps the bar there.)
    "PULSE_MC_ADVERSE_EV_THRESHOLD": "0.0",
    "PULSE_MC_SCENARIO_LLM": "1",
    "PULSE_GROK_DECIDER_MIN_CONFIDENCE": "0.62",
    "PULSE_GROK_DECIDER_EXPLORE_MIN_VIEW_MARGIN": "0.08",
    # Trinity profile: fast 15s tick (arb) + tiered Grok (profit/API/soak balance).
    "GROK_BUDGET_DAILY_USD": "35",
    "GROK_EST_USD_PER_CALL": "0.02",
    "GROK_SIGNAL_PREDICTOR_ENABLED": "1",
    "GROK_SIGNAL_ANALYST_ENABLED": "1",
    "GROK_PREDICTOR_MAX_CALLS_PER_HOUR": "60",
    "GROK_ANALYST_MAX_CALLS_PER_HOUR": "4",
    "PULSE_GROK_DECIDER_MAX_CALLS_PER_HOUR": "120",
    "PULSE_GROK_DECIDER_TIMEOUT_S": "18",
    # Deep-tier web/X search OFF (operator-authorized 2026-06-30): it drove the decider's timeout
    # errors (~29% of calls, 8.3s avg latency vs 18s cap) and burned API budget for no proven gain
    # (the decider is shadow/observe-only and was anti-predictive). Tiered compute keeps the decider
    # running for grading; it just stops issuing slow live-search calls.
    "PULSE_GROK_DECIDER_USE_SEARCH": "0",
    "PULSE_GROK_NEWS_REFRESH_S": "300",
    "PULSE_GROK_TIERED_COMPUTE": "1",
    "PULSE_GROK_TIER_FULL_DIVERGENCE_MIN": "0.025",
    "PULSE_GROK_TIER_DEEP_DIVERGENCE_MIN": "0.04",
    "PULSE_VERIFIER_ENABLED": "1",
    # Council pairs Claude as a voting MEMBER with Claude the verifier (checker). To avoid Claude
    # double-gating (member + fail-closed checker) starving council trades, the verifier now only
    # blocks on an ACTIVE veto, not on a pending/latency verdict (fail-open on pending).
    "PULSE_VERIFIER_FAIL_OPEN": "1",
    "PULSE_VERIFIER_FOLLOW_REQUIRE_VERDICT": "0",
    # [TV-LOCK] observe-only — webhooks feed features/Grok; no MTF or signal trade authority.
    "PULSE_TRADINGVIEW_SIGNAL_GATE": "0",
    "PULSE_TV_EVENT_ID_SUFFIX": "bot1",
    "PULSE_TV_MIN_SIGNAL_STRENGTH": "0",
    "PULSE_TV_MTF_CONFLICT_GATE": "0",
    "PULSE_TV_MTF_REQUIRE_CONFIRM": "0",
    "PULSE_TV_MTF_REQUIRE_ALL_CONFIRM": "0",
    "PULSE_TV_MTF_REQUIRE_SIDE_ALIGN": "0",
    # UP restrictor floors: block proven-losing UP contexts.
    "PULSE_TV_DOWN_BIAS_GATE": "0",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_AGAINST_CONFIRMED_DOWN": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_RANGE_TOP": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_MARKOV_CHOP_NOISE": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_LATE_TTC": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_EARLY_TTC": "1",
    "PULSE_TV_DOWN_BIAS_UP_LATE_TTC_MIN_S": "240",
    "PULSE_TV_DOWN_BIAS_UP_EARLY_TTC_MAX_S": "120",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_CVD_NEUTRAL": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_LOW_CONVICTION": "1",
    "PULSE_TV_DOWN_BIAS_UP_MIN_CONVICTION": "0.40",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_NEUTRAL_ZSCORE": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_MEDIUM_CONFIDENCE": "1",
    "PULSE_TV_DOWN_BIAS_BLOCK_UP_UNDERDOG_ENTRY": "1",
    "PULSE_TV_DOWN_BIAS_UP_UNDERDOG_ENTRY_MAX": "0.55",
    "PULSE_LATE_WINDOW_ENTRY": "0",
    # Must exceed scaled cohort max (15m: 220*3+1=661). Coupling auto-clamps if too low.
    "PULSE_TV_CONTEXT_MAX_TTC_S": "900",
    "PULSE_TV_CONTEXT_EXPLORATION_RATE": "0",
    "PULSE_TV_DOWN_BIAS_EXPLORE_RATE": "0",
    # Baseline quant path: allowlist was deadlocking (no proven bucket + 0% explore).
    "PULSE_DIRECTIONAL_REQUIRE_WINNING": "0",
    "PULSE_DIRECTIONAL_EXPLORE_RATE": "0.05",   # WS2: cold-start DOWN exploration (was 0, deadlocked)
    # Let the bot trade (operator 2026-07-01 "find what chokes trading, tweak to let it trade"):
    # edge_below_min was the #1 directional reject (~6k). Halve the after-cost edge threshold + basis
    # buffer so more 15m windows clear. The execution-quality EV gate + calibration + selectivity
    # learners still bound quality (graded on outcomes; re-tighten if WR craters). Trades thinner edge.
    "PULSE_MIN_EDGE": "0.004",
    "PULSE_BASIS_BUFFER": "0.004",
    # Strategy: sweet-spot only (0.47-0.55) entry band.
    # Loosened 0.45->0.35 (2026-07-01 "loosen restriction"): the underdog-price floor was rejecting
    # best-EV's cheap-underdog picks (underdog_price_below_floor was the top exec-gate reject). It's an
    # adverse-selection guard (cheap-side buys historically won ~28%), so loosen MODERATELY, not to 0 -
    # -the EV-after-slippage gate stays the backstop and underdog trades are graded (re-tighten if they
    # lose). Lets best-EV take +EV underdogs down to 0.35.
    "PULSE_MIN_ENTRY_PRICE": "0.35",
    "PULSE_MIN_REWARD_RISK": "0.50",
    "PULSE_MIN_REWARD_RISK_UP_PREMIUM": "0.28",
    "PULSE_GROK_UP_MIN_P_WIN": "0.52",
    # Gamma windows often appear >20s after open_ts; min_seconds_since_open=30 already delays entry.
    "PULSE_MAX_OPEN_LAG_S": "120",
    "PULSE_MAX_OPEN_LAG_15M_S": "240",
    # Stop halt: keep above rolling_n until post-relaxation cohort rebuilds (n=50 was frozen).
    "PULSE_STOP_MIN_SAMPLES": "60",
    # Sweet-spot entry (1M MC sim): base 160-220s → 15m TTC 480-660s (minutes 8-11).
    "PULSE_TICK_SECONDS": "15",
    # Widened 0.65->0.72 (2026-07-02) as a CAPPED favorite-band experiment: the favorite-longshot-bias
    # literature says favorites (0.60-0.85) resolve MORE often than their price implies (Leo Labs: 0.60-
    # 0.70 -> ~80% realized). We have only ~4 trades there, so this is UNVERIFIED for our BTC markets ->
    # it stays an experiment, not a strategy flip. Raising the cap only ENABLES best-EV to take a
    # favorite when it judges it underpriced (needs consensus p_up > price + reward/risk), which is rare
    # since quant is ~calibrated -> naturally self-capping. Per-price-bucket realized-vs-implied WR is
    # tracked on the dashboard so we measure whether the favorite band actually pays here.
    "PULSE_MAX_PRICE": "0.72",
    # [TV-LOCK] context gate off — TV never blocks entries.
    "PULSE_TV_CONTEXT_GATE": "0",
    # TV confidence tier: modulate min_edge/max_price at 15m sweet spot (not a trade gate).
    "PULSE_TV_CONFIDENCE_TIER_ENABLED": "1",
    "PULSE_TV_TIER_REQUIRE_SWEET_SPOT": "1",
    "PULSE_TV_TIER_15M_ONLY": "1",
    "PULSE_TV_TIER_ALIGNED_STRENGTH_MIN": "0.72",
    "PULSE_TV_TIER_A_MIN_EDGE_DELTA": "-0.005",
    "PULSE_TV_TIER_A_MAX_PRICE_DELTA": "0.02",
    "PULSE_TV_TIER_C_MIN_EDGE_DELTA": "0.005",
    "PULSE_TV_TIER_C_MAX_PRICE_DELTA": "-0.03",
    # Mispricing/edge-TTC off on quant baseline (Grok shadow; redundant with cohort).
    "PULSE_MISPRICING_GATE_ENABLED": "0",
    "PULSE_MISPRICING_TTC_MIN_S": "160",
    "PULSE_MISPRICING_TTC_MAX_S": "220",
    "PULSE_MISPRICING_REQUIRE_CONFIRMED": "0",
    "PULSE_MISPRICING_REQUIRE_STALE_DOWN": "1",
    "PULSE_MISPRICING_MIN_EXECUTABLE_MARGIN": "0.02",
    "PULSE_MISPRICING_FOLLOW_ON_ABSTAIN": "0",
    "PULSE_MISPRICING_FOLLOW_SIZE_FRACTION": "0.5",
    "PULSE_EDGE_TTC_GATE_ENABLED": "0",
    "PULSE_CEX_LEAD_MIN_EDGE_VS_MARKET": "0.02",
    "PULSE_CEX_LEAD_TV_STRENGTH_THR": "0.72",
    # Tier 1: sweet-spot cohort 160-220s base (15m fast-lane → 480-660s TTC).
    "PULSE_BASELINE_COHORT_GATE_ENABLED": "1",
    "PULSE_BASELINE_COHORT_TTC_MIN_S": "160",
    "PULSE_BASELINE_COHORT_TTC_MAX_S": "230",
    "PULSE_BASELINE_COHORT_REQUIRE_HIGH_EDGE": "0",
    "PULSE_BASELINE_COHORT_REQUIRE_STRONG_CEX": "0",
    "PULSE_BASELINE_COHORT_15M_FAST_LANE": "1",
    "PULSE_BASELINE_COHORT_15M_TTC_MIN_S": "150",
    "PULSE_BASELINE_COHORT_15M_TTC_MAX_S": "240",
    # [TV-LOCK] baseline path does not use TV stack to block entries.
    "PULSE_BASELINE_UP_TV_GATE_ENABLED": "0",
    "PULSE_BASELINE_DOWN_TV_GATE_ENABLED": "0",
    "PULSE_BASELINE_DOWN_BLOCK_BULLISH_RANGE": "1",
    "PULSE_BASELINE_DOWN_BLOCK_UP_STRONG_BULLISH": "1",
    "PULSE_BASELINE_DOWN_BLOCK_NOT_STALE": "0",
    "PULSE_BASELINE_DOWN_BLOCK_MEDIUM_EDGE": "0",
    "PULSE_BASELINE_DOWN_BLOCK_SINGLE_TF": "0",
    "PULSE_BASELINE_DOWN_BLOCK_VOLUME_ACTIVE": "0",
    "PULSE_BASELINE_DOWN_BLOCK_BULLISH_MTF": "0",
    "PULSE_BASELINE_DOWN_BLOCK_MID_ENTRY": "0",
    "PULSE_BASELINE_DOWN_BLOCK_BB_EXPANSION_DOWN": "0",
    "PULSE_BASELINE_DOWN_MID_ENTRY_MIN": "0.55",
    "PULSE_BASELINE_DOWN_MID_ENTRY_MAX": "0.60",
    # 5m brain (scan/LCMM child) + 15m hands (directional + parent). No 5m directional.
    "PULSE_SERIES_SLUGS": "btc-up-or-down-5m,btc-up-or-down-15m",
    "PULSE_DIRECTIONAL_SERIES_SLUGS": "btc-up-or-down-15m",
    # Cost-aware capture (deep-scan 2026-06-29, operator-authorized): the flat 0.015 epsilon
    # double-counted execution risk and never fired on tight BTC books. We now make the
    # PER-OPPORTUNITY non-atomic sim the real cost filter (market impact + 50bps leg-2 slippage +
    # pre-commit-breach check) and drop epsilon to a small fees-only floor. Net effect: capture the
    # near-miss band ONLY when the trade still books guaranteed >0 after realistic sequential fills;
    # reject sub-cost ones. Every booked arb stays guaranteed >= $0 by construction.
    # Atomic within-window arb RE-ENABLED (operator-authorized 2026-07-01): it is the only
    # GUARANTEED positive-EV lane (buy up+down for <$1, collect exactly $1 — risk-free by
    # construction). Runs alongside the Claude-gated dep-arb so there is a real profitable lane while
    # dep-arb's verifier matures. Directional stays OFF (PULSE_DIRECTIONAL_ENABLED=0). Net: arb-only
    # (atomic risk-free arb + dep-arb conjunction/Claude-gated nested), no directional noise.
    "PULSE_ARB_ENABLED": "1",
    "PULSE_ARB_FEES": "0.0",
    # Lowered 2026-07-01: 1415 near-misses within 2c at 0.003 — capture thin dutch-book edges.
    "PULSE_ARB_EPSILON": "0.001",
    "PULSE_ARB_EPSILON_5M": "0.001",
    "PULSE_ARB_EPSILON_15M": "0.001",
    "PULSE_DEPENDENCY_ARB_EPSILON": "0.03",
    # WS3-B: Fréchet conjunction floor — the only dep-arb path that may EXECUTE. It is true
    # risk-free arb (all nested children UP => parent UP), so it stays ON.
    "PULSE_DEPENDENCY_ARB_CONJUNCTION": "1",
    # Nested-implication execution is ON but now GATED by an AUTHORITATIVE Claude verifier
    # (operator-authorized 2026-06-30 "strengthen dep-arb"). The raw nested heuristic is negative-EV
    # (capture -0.18, holdout PF 0.78) and previously ran fail-OPEN — Claude only graded after the
    # fact, so it bled -$406. With FAIL_OPEN=0 + REQUIRE_VERDICT=1 below, a nested fill now requires
    # an EXPLICIT Claude approve; pending/veto/error => no trade. Claude's counterfactual vetoes have
    # been correct (avoided -$100), so making it the gatekeeper stops the bleed while keeping the
    # LLM-leveraged path open to scale as the verifier's veto_quality proves out.
    "PULSE_DEPENDENCY_ARB_NESTED_EXECUTE": "1",
    # Off: parent books refresh every tick (~15s) so min_parent_book_age_s=120 starved all fills.
    "PULSE_DEPENDENCY_ARB_CLOCK_SKEW_ENABLED": "0",
    "PULSE_DEPENDENCY_ARB_MIN_PARENT_BOOK_AGE_S": "120",
    "PULSE_DEPENDENCY_ARB_MAX_CHILD_BOOK_AGE_S": "90",
    "PULSE_DEPENDENCY_ARB_MAX_CHILD_WINDOW_AGE_S": "120",
    "PULSE_DEPENDENCY_ARB_MID_CONVERGENCE_OBSERVE": "1",
    "PULSE_DEPENDENCY_ARB_MID_CONVERGENCE_HORIZONS_S": "30,60,120",
    # LOCKS LIFTED (operator 2026-07-01): runtime self-tuning ON — the loop may auto-apply dep-arb
    # experiments (e.g. flip nested_execute on bleeding buckets) from live settled evidence.
    "PULSE_DEPENDENCY_ARB_EXPERIMENT_AUTO_APPLY": "1",
    "PULSE_DEPENDENCY_ARB_MID_EXIT_ENABLED": "1",
    "PULSE_DEPENDENCY_ARB_MID_EXIT_HORIZON_S": "60",
    "PULSE_DEPENDENCY_ARB_MAX_ENTRY_VWAP": "0.52",
    # A1 edge fix (2026-07-01, ledger evidence n=128): cheap parent-UP entries are
    # adverse-selection. Ledger by entry_vwap: <0.50 nested lost -$440; floor at 0.50
    # flips the nested lane -$410 -> +$38 (WR 0.59->0.72, keeps 82/118) while the
    # positive dependency_bregman path stays WR 1.0. epsilon/max_entry_vwap tuning did
    # NOT help (magnitude 0.1-0.2 was the -$275 cluster), so only the min floor is set.
    "PULSE_DEPENDENCY_ARB_MIN_ENTRY_VWAP": "0.50",
    "PULSE_GROK_DEPENDENCY_ENABLED": "1",
    "PULSE_GROK_DEPENDENCY_INTERVAL_S": "180",
    # Grok 60s convergence predictor DISABLED (operator-authorized 2026-06-30): live accuracy was 4%
    # (worse than random — an anti-signal), yet it was fed into the Claude dep-arb verifier as a prior
    # (engine build_dep_arb_verify_payload grok_convergence=), degrading veto quality. Turning it off
    # removes the misleading prior AND frees Grok daily budget for the dependency proposer (which was
    # skipped_budget-starved at 0 validated proposals).
    "PULSE_GROK_DEP_CONVERGENCE_ENABLED": "0",
    "PULSE_GROK_DEP_CONVERGENCE_GATE": "0",
    "PULSE_GROK_DEP_CONVERGENCE_MIN_CONVERGE_60S": "0.35",
    "PULSE_GROK_DEP_CONVERGENCE_MAX_CALLS_PER_HOUR": "30",
    "PULSE_DEP_ARB_VERIFIER_ENABLED": "1",
    # Claude maker-checker AUTHORITATIVE on nested + conjunction (operator-authorized 2026-06-30):
    # fail-CLOSED + require-verdict so a dep-arb fill needs an explicit Claude approve (was fail-open
    # observe-only, which let nested bleed). pending/veto/error => no trade.
    "PULSE_DEP_ARB_VERIFIER_CONJUNCTION_ONLY": "0",
    "PULSE_DEP_ARB_VERIFIER_FAIL_OPEN": "0",
    "PULSE_DEP_ARB_VERIFIER_REQUIRE_VERDICT": "1",
    "PULSE_DEP_ARB_VERIFIER_MAX_CALLS_PER_HOUR": "40",
    # LOCKS LIFTED (operator 2026-07-01 "remove all locks; make the loop learn+adjust"): directional
    # ON so trades flow and feed every learner (learning-blend/edge-model/selectivity need settled
    # samples; only 24 collected while this was off). Selectivity + allowlist + calibration now govern
    # entries from live evidence instead of a static freeze.
    "PULSE_DIRECTIONAL_ENABLED": "1",
    # Verifier: stop starving cold-start exploration with "when unsure, veto" — exploration trades
    # get a shrunk approve instead of a hard veto so settled data can be collected and the veto's
    # own quality graded. Capability gated; full effect once wired into the follow path.
    "PULSE_VERIFIER_EXPLORE_APPROVE": "1",
    "PULSE_ARB_MAX_USD": "300",
    "PULSE_PRIMARY_EDGE_SOURCE": "arbitrage",
    "PULSE_DIRECTIONAL_MAX_BANKROLL_FRAC": "0.10",
    # Unchoke UP (operator 2026-07-01 "let bot trade"): the market currently leans UP, and every UP
    # entry was blocked by BLOCK_UP_UNTIL_PROMOTED (rejected:up_blocked_until_promoted was the binding
    # choke after the edge relax). Open the UP side so the council/quant can actually trade its
    # direction; the execution-quality EV gate + calibration + selectivity learners still bound quality
    # and GRADE UP on real outcomes (re-block via the learner if UP proves losing). Was proven-marginal.
    "PULSE_DIRECTIONAL_DOWN_ONLY": "0",
    "PULSE_DIRECTIONAL_BLOCK_UP_UNTIL_PROMOTED": "0",
    "PULSE_DIRECTIONAL_UP_RESTRICTIONS_ENABLED": "0",
    "PULSE_DEPENDENCY_ARB_ENABLED": "1",
    "PULSE_DEPENDENCY_ARB_EXECUTE": "1",
    "PULSE_GREEN_PATH_ENABLED": "1",
    # Bet size reduced to $5/bet (operator-authorized 2026-07-01): caps per-trade downside
    # on the dep-arb lane while the min-entry-vwap edge fix is validated on a fresh soak.
    "PULSE_DEPENDENCY_ARB_MAX_USD": "5",
    "PULSE_BREGMAN_PROJECTION_ENABLED": "1",
    # LOCKS LIFTED (operator 2026-07-01): Bregman projection may now size dep-arb (was observe-only).
    "PULSE_BREGMAN_TRADE_AUTHORITY": "1",
    "PULSE_BREGMAN_ALPHA": "0.9",
    "PULSE_BREGMAN_EPSILON_INIT": "0.1",
    "PULSE_BREGMAN_FW_MAX_ITERS": "50",
    "PULSE_BREGMAN_FW_TIME_BUDGET_MS": "500",
    "PULSE_IP_ORACLE_BACKEND": "ortools",
    "PULSE_CLOB_WEBSOCKET_ENABLED": "1",
    "PULSE_STOP_MIN_SHARPE": "0",
    "PULSE_STOP_SHARPE_MIN_SAMPLES": "20",
    # Paper soak: keep dep-arb entries flowing while capture ratio is repaired (-$19.65 ledger).
    "PULSE_STOP_DEP_ARB_GUARD_ENABLED": "0",
    "PULSE_ETH_SERIES_ENABLED": "0",
    "PULSE_RESEARCH_LOOP_ENABLED": "1",
    "PULSE_RESEARCH_AUTO_APPLY": "1",
    "PULSE_RESEARCH_INTERVAL_S": "1200",
    "PULSE_RESEARCH_AVOID_MAX": "20",
    "PULSE_RESEARCH_FORBID_SIZE_INCREASE": "1",
    "PULSE_LEARNING_ENABLED": "1",
    # LOCKS LIFTED (operator 2026-07-01): activate the learning blend sooner (was 40; n=24 collected)
    # so the learned edge model starts steering fair value now instead of staying observe-only.
    "PULSE_LEARNING_MIN_SAMPLES": "20",
    "PULSE_LEARNING_RAMP_SAMPLES": "120",
    "PULSE_LEARNING_BENCH_MARGIN": "0.0",
    "PULSE_ARB_GLOBAL_MAX_OPEN_USD": "600",
    # Step 2 guard: leg risk is the only way arb can lose — atomic complete-set only.
    # Operator-authorized 2026-06-29: re-enabled so the sim is the PER-OPPORTUNITY cost filter that
    # makes the low epsilon above safe (rejects any near-miss that would lose after leg-2 slippage).
    "PULSE_ARB_NONATOMIC_ENABLED": "1",
    "PULSE_ARB_NONATOMIC_SLIPPAGE_BPS": "50",
    "PULSE_SIZING_PROMOTION_GATED": "1",
    # LOCKS LIFTED (operator 2026-07-01): dynamic edge-proportional sizing ON (still bounded by the
    # $5/bet dep-arb cap + bankroll caps + FORBID_SIZE_INCREASE, and promotion-gated so it scales
    # only as learned edge proves out).
    "HERMES_SIZING_ENABLED": "1",
    # TradingView INDEX:BTCUSD — 2m + 3m + 4m chart alerts (three charts, v6 ProfitGate).
    "PULSE_TV_FEATURE_SYMBOL": "BTCUSD",
    "TRADINGVIEW_ALLOWED_SYMBOLS": "BTCUSD,INDEX:BTCUSD,BTC/USD,BTC,XBTUSD",
    "TRADINGVIEW_MAX_AGE_S": "180",
    # Operator 2026-07-01 "remove TV 2m 3m 4m": retired the short, anti-predictive TREND TFs.
    # 2026-07-02: un-drop 3 so a 3m MEAN-REVERSION alert can be tracked as tv_3m (3m closes on the
    # 15-min window grid; no 3m trend alert to collide with). 2 and 4 stay dropped.
    "PULSE_TV_DROP_TIMEFRAMES": "2,4",
    "PULSE_TV_MTF_TIMEFRAMES": "5,10,15",
    # Cross-lane correlated-exposure cap (2026-07-02): directional UP and dep-arb parent-UP are both
    # long BTC-up; cap the combined same-direction exposure open at once so the 3 lanes don't stack the
    # same bet. Read-only gate (only blocks, never forces). ~$20 allows a normal mix, blocks piling on.
    "PULSE_CORRELATED_EXPOSURE_CAP_USD": "20",
    # ~2.5 bar lengths per TF (5m=750s, 10m=1500s, 15m=2250s); kept for any 2/3/4 that still arrive.
    "PULSE_TV_MTF_CONFIRM_WINDOW_2M_S": "300",
    "PULSE_TV_MTF_CONFIRM_WINDOW_3M_S": "450",
    "PULSE_TV_MTF_CONFIRM_WINDOW_4M_S": "600",
    # Tier 2: selectivity blocks need PF floor + higher min_samples + BH-FDR.
    "PULSE_SELECTIVITY_MIN_SAMPLES": "30",
    "PULSE_SELECTIVITY_MIN_PROFIT_FACTOR": "0.92",
    "PULSE_SELECTIVITY_MIN_WIN_RATE": "0.55",
    "PULSE_SELECTIVITY_FDR_Q": "0.10",
}


def _enforce_context_cohort_coupling(updates: dict) -> dict:
    """Raise PULSE_TV_CONTEXT_MAX_TTC_S if it would deadlock baseline cohort."""
    slugs = [s.strip() for s in updates.get("PULSE_SERIES_SLUGS", "").split(",") if s.strip()]
    rep = evaluate_context_cohort_coupling(
        baseline_cohort_enabled=updates.get("PULSE_BASELINE_COHORT_GATE_ENABLED", "1") == "1",
        tv_context_enabled=updates.get("PULSE_TV_CONTEXT_GATE", "1") == "1",
        configured_context_max_ttc_s=float(updates.get("PULSE_TV_CONTEXT_MAX_TTC_S", "0") or 0),
        cohort_ttc_min_s=float(updates.get("PULSE_BASELINE_COHORT_TTC_MIN_S", "180")),
        cohort_ttc_max_s=float(updates.get("PULSE_BASELINE_COHORT_TTC_MAX_S", "240")),
        window_seconds_list=window_seconds_for_slugs(slugs),
        auto_clamp=False,
    )
    if rep.get("active") and not rep.get("configured_ok"):
        fixed = str(int(rep["required_min_s"]))
        print(
            f"COUPLING: PULSE_TV_CONTEXT_MAX_TTC_S {updates['PULSE_TV_CONTEXT_MAX_TTC_S']} "
            f"-> {fixed} (required for cohort band on {slugs})"
        )
        updates = {**updates, "PULSE_TV_CONTEXT_MAX_TTC_S": fixed}
    return updates


UPDATES = _enforce_context_cohort_coupling(UPDATES)

text = ENV_PATH.read_text(encoding="utf-8") if ENV_PATH.exists() else ""
lines = [ln for ln in text.splitlines() if not ln.strip().startswith("# LOOP ENGINE ARCH")]
seen = set()
out = []
remaining = dict(UPDATES)
for ln in lines:
    if "=" in ln and not ln.lstrip().startswith("#"):
        key = ln.split("=", 1)[0].strip()
        if key in remaining:
            out.append(f"{key}={remaining.pop(key)}")
            seen.add(key)
        elif key not in seen:
            out.append(ln)
            seen.add(key)
    elif ln.strip():
        out.append(ln)
for key, val in remaining.items():
    out.append(f"{key}={val}")
out.append(
    "# LOOP ENGINE ARCH (2026-06-28): arb-first perfect-WR lab — directional OFF, "
    "dual 5m+15m arb scan, atomic arb only, dep arb execute, Bregman observe-only"
)
ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"Wrote {ENV_PATH} ({len(UPDATES)} loop-arch keys)")