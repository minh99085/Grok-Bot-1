from loop.connectors.tradingview import TvSignalStore, parse_alert


def test_parse_btcusdt_alert():
    sig = parse_alert(
        {
            "symbol": "BTCUSDT",
            "direction": "long",
            "strength": "strong",
            "indicator": "hermes_pulse",
            "price": 64000.0,
        },
        now_ms=1_700_000_000_000,
    )
    assert sig.symbol == "BTCUSDT"
    assert sig.direction == "UP"
    assert sig.level == "UP_STRONG"


def test_store_latest_for_symbol(tmp_path):
    store = TvSignalStore(str(tmp_path / "tv.jsonl"))
    store.add(parse_alert({"symbol": "ETHUSDT", "direction": "down"}))
    store.add(parse_alert({"symbol": "BTCUSDT", "direction": "up", "strength": 2}))
    latest = store.latest_for_symbol("BTCUSDT")
    assert latest is not None
    assert latest.direction == "UP"