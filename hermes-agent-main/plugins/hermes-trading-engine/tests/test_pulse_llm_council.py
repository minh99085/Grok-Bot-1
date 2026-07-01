"""LLM council: evidence-weighted ensemble of quant + Grok + Claude directional views (PAPER)."""

from __future__ import annotations

from engine.pulse.llm_council import council_consensus, member_weight, LLMCouncil, best_ev_side


def test_best_ev_picks_cheap_underdog_when_underpriced():
    # p_up=0.55, UP favorite priced 0.90 (ev -0.35), DOWN underdog priced 0.30 (ev 0.45-0.30=0.15).
    side, ev = best_ev_side(0.55, up_ask=0.90, down_ask=0.30, min_edge=0.01)
    assert side == "down" and ev == 0.15          # takes the cheap +EV underdog, not the favorite


def test_best_ev_picks_up_when_up_is_cheap_and_positive():
    side, ev = best_ev_side(0.60, up_ask=0.50, down_ask=0.55, min_edge=0.01)
    assert side == "up" and ev == 0.10


def test_best_ev_no_trade_when_both_overpriced():
    # both sides -EV (efficient/expensive market) -> no trade
    side, ev = best_ev_side(0.55, up_ask=0.62, down_ask=0.50, min_edge=0.01)
    assert side is None                            # best ev = -0.05 (down) < min_edge


def test_best_ev_handles_missing_book():
    side, ev = best_ev_side(0.7, up_ask=None, down_ask=0.20, min_edge=0.01)
    assert side == "down" and ev == 0.10
    assert best_ev_side(None, 0.5, 0.5)[0] is None


def test_consensus_trades_when_members_agree_with_margin():
    votes = [
        {"name": "quant", "p_up": 0.62, "weight": 1.0},
        {"name": "grok", "p_up": 0.60, "weight": 0.5},
        {"name": "claude", "p_up": 0.58, "weight": 0.7},
    ]
    out = council_consensus(votes, min_agreement=0.6, min_margin=0.02, min_members=2)
    assert out["trade"] is True
    assert out["side"] == "up"
    assert out["agreement"] == 1.0
    assert out["consensus_p_up"] > 0.5


def test_consensus_no_trade_insufficient_members():
    out = council_consensus([{"name": "quant", "p_up": 0.7, "weight": 1.0}], min_members=2)
    assert out["trade"] is False and out["reason"] == "insufficient_members"


def test_consensus_no_trade_low_margin():
    votes = [{"name": "quant", "p_up": 0.505, "weight": 1.0},
             {"name": "grok", "p_up": 0.51, "weight": 1.0}]
    out = council_consensus(votes, min_margin=0.05, min_members=2)
    assert out["trade"] is False and out["reason"] == "low_margin"


def test_consensus_no_trade_on_disagreement():
    # High-weight members split around 0.5 -> low weighted agreement.
    votes = [{"name": "quant", "p_up": 0.75, "weight": 1.0},
             {"name": "grok", "p_up": 0.25, "weight": 1.0}]
    out = council_consensus(votes, min_agreement=0.6, min_margin=0.0, min_members=2)
    # consensus is exactly 0.5 -> side up, but only half the weight agrees -> below 0.6
    assert out["agreement"] == 0.5
    assert out["trade"] is False and out["reason"] == "low_agreement"


def test_member_weight_cold_warm_and_antipredictive():
    # cold: below min_samples -> prior
    assert member_weight(0, 0, prior=0.4, floor=0.1, min_samples=20) == 0.4
    # warm anti-predictive (30% accuracy) -> collapses to floor
    assert member_weight(9, 30, prior=0.4, floor=0.1, min_samples=20, scale=8.0) == 0.1
    # warm proven (~80% accuracy) -> well above floor
    w = member_weight(24, 30, prior=0.4, floor=0.1, min_samples=20, scale=8.0)
    assert w > 0.5


def test_council_learns_to_trust_proven_member_and_downweight_bad_one():
    c = LLMCouncil(enabled=True, min_samples=20, min_members=2, min_margin=0.02)
    # grok is anti-predictive (always says up, market goes down); claude is accurate.
    for _ in range(30):
        c.grade({"grok": 0.8, "claude": 0.2, "quant": 0.5}, outcome_up=False)
    rep = c.report()
    assert rep["members"]["grok"]["weight"] == c.weight_floor      # collapsed to floor
    assert rep["members"]["claude"]["weight"] > c.weight_floor      # earned weight
    # Now a window where grok(up) disagrees with claude(down): the proven claude should dominate.
    out = c.decide({"grok": 0.70, "claude": 0.30, "quant": 0.5})
    assert out["side"] == "down"
    assert out["trade"] is True


def test_council_fail_open_when_no_views():
    c = LLMCouncil(enabled=True, min_members=2)
    out = c.decide({"grok": None, "claude": None, "quant": None})
    assert out["trade"] is False and out["reason"] == "insufficient_members"


def test_state_roundtrip():
    c = LLMCouncil(enabled=True)
    c.grade({"quant": 0.6, "grok": 0.4}, outcome_up=True)
    st = c.to_state()
    c2 = LLMCouncil(enabled=True)
    c2.load_state(st)
    assert c2.to_state()["stats"] == st["stats"]
    assert c2.graded == 1


def test_from_env_reads_council_flags(monkeypatch):
    from engine.pulse.engine import PulseConfig
    monkeypatch.setenv("PULSE_LLM_COUNCIL_ENABLED", "1")
    monkeypatch.setenv("PULSE_LLM_COUNCIL_MIN_AGREEMENT", "0.7")
    monkeypatch.setenv("PULSE_CLAUDE_DECIDER_ENABLED", "1")
    c = PulseConfig.from_env()
    assert c.llm_council_enabled is True
    assert c.llm_council_min_agreement == 0.7
    assert c.claude_decider_enabled is True


def test_engine_status_exposes_council(tmp_path):
    from engine.pulse.engine import PulseEngine, PulseConfig
    from engine.pulse.price import PulsePriceFeed
    from engine.pulse.fair_value import RollingVol

    class _Mkt:
        def active_windows(self, now=None, **kw):
            return []

        def hydrate_books(self, w):
            return w

    feed = PulsePriceFeed(fetcher=lambda: 64000.0, source_name="rtds_chainlink",
                          vol=RollingVol(window_s=900, min_samples=2), max_open_lag_s=9999.0)
    cfg = PulseConfig(tick_seconds=1.0, data_dir=str(tmp_path), tradingview_webhook_port=0,
                      llm_council_enabled=True)
    eng = PulseEngine(cfg, market_feed=_Mkt(), price_feed=feed)
    st = eng.status()
    assert st["llm_council"]["enabled"] is True
    assert "members" in st["llm_council"]
    # tick with no windows must not raise (council path guarded / fail-open)
    eng.tick(now=10_000_100.0)
