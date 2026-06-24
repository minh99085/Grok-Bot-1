import os
import time

from grok_bot.chainlink_reader import parse_latest_round_data
from grok_bot.ingest import scripted_ingestor
from grok_bot.price_stack import PriceStack, blend_leading, estimate_p_up
from grok_bot.reference_feeds import PriceSample, ScriptedCexFeed
from loop.connectors.tradingview import TvSignalStore, parse_alert


def _fake_chainlink_http(_url, _payload, _timeout):
    # answer = 64000 * 1e8 as int256 hex word
    answer = int(64000 * 1e8)
    if answer < 0:
        answer += 1 << 256
    word = format(answer, "064x")
    updated = format(int(time.time()), "064x")
    result = "0x" + ("0" * 64) + word + ("0" * 64) + updated + ("0" * 64)
    return {"result": result}


def test_leading_feeds_rank_ahead_of_chainlink():
    now = int(time.time() * 1000)

    def cex_fn(ts):
        return [
            PriceSample("binance", 64100.0, ts, ts, "leading"),
            PriceSample("coinbase", 64090.0, ts, ts, "leading"),
        ]

    store = TvSignalStore(os.devnull)
    store.add(parse_alert({"symbol": "BTCUSDT", "direction": "UP", "price": 64105.0}, now_ms=now))

    ing = scripted_ingestor(
        cex_fn=cex_fn,
        chainlink_fn=_fake_chainlink_http,
        tv_store=store,
        window_start=64000.0,
    )
    data = ing.ingest(now_ms=now)
    stack = data["price_stack"]

    assert stack["leading_price"] > stack["chainlink_price"]
    assert stack["lead_vs_chainlink_bps"] > 0
    assert data["implied_direction"] == "UP"
    assert data["p_up"] > 0.55
    assert data["feed_order"][0] == "binance"
    assert data["feed_order"][-1] == "chainlink_settlement"


def test_blend_requires_leading_sources():
    now = int(time.time() * 1000)
    leading = blend_leading(
        [
            PriceSample("binance", 65000, now, now),
            PriceSample("coinbase", 65010, now, now),
        ],
        None,
        now_ms=now,
    )
    assert leading.source_count == 2
    assert 65000 <= leading.price <= 65010


def test_chainlink_parse():
    answer = int(64000 * 1e8)
    word = format(answer, "064x")
    h = "0x" + ("0" * 64) + word + ("0" * 64) + format(1_700_000_000, "064x") + ("0" * 64)
    parsed = parse_latest_round_data(h)
    assert parsed is not None
    assert abs(parsed["price"] - 64000.0) < 0.01


def test_estimate_p_up_tv_nudge():
    from grok_bot.price_stack import LeadingSnapshot

    leading = LeadingSnapshot(64005.0, 3, ("binance", "coinbase", "tradingview"), 0.8, "UP", 64005.0)
    p_up, direction, edge = estimate_p_up(window_start=64000.0, leading=leading, chainlink=None)
    assert direction == "UP"
    assert p_up > 0.5
    assert edge > 0