from grok_bot.claude_verifier import ClaudeVerifier
from grok_bot.config import BotConfig
from grok_bot.grok_maker import GrokMaker
from grok_bot.pipeline import PipelineContext, build_signal_candidate, verify_with_checker
from loop.connectors.tradingview import TvSignalStore, parse_alert


def test_config_llm_roles():
    cfg = BotConfig(xai_api_key="x", anthropic_api_key="c")
    assert cfg.llm_roles() == {"maker": "grok/xAI", "checker": "claude/anthropic"}


def test_grok_maker_transport():
    maker = GrokMaker(
        api_key="k",
        transport=lambda _k, _m, _s, _u: {
            "bias": "up",
            "confidence": 0.8,
            "size_hint": 0.5,
            "reason": "test",
        },
    )
    d = maker.propose({"x": 1})
    assert d.called and d.bias == "up" and d.size_hint == 0.5


def test_claude_fails_closed_without_approval():
    claude = ClaudeVerifier(
        api_key="k",
        transport=lambda _k, _m, _s, _u: {"approved": False, "reasons": ["no edge"], "confidence": 0.1},
    )
    signal = {"sharpe": 2.0, "max_drawdown": 0.05, "newey_west_t": 2.5, "oos_years": 2.5}
    ctx = PipelineContext(market={}, tv_signal=None, maker=None, numeric_verdict=None, claude_review=None)
    verdict, ctx2 = verify_with_checker(signal, ctx, claude=claude)
    assert not verdict.passed
    assert ctx2.claude_review["approved"] is False


def test_tv_signal_tags_candidate(tmp_path):
    store = TvSignalStore(str(tmp_path / "tv.jsonl"))
    store.add(parse_alert({"symbol": "BTCUSDT", "direction": "UP", "strength": "strong"}))
    market = {"symbol": "btc-updown-5m", "sharpe": 1.9, "max_drawdown": 0.03,
              "newey_west_t": 2.2, "oos_years": 2.1, "edge": 0.01, "notional": 100}
    signal, ctx = build_signal_candidate(market, tv_store=store)
    assert signal is not None
    assert signal["tv_level"] == "UP_STRONG"
    assert ctx.tv_signal is not None