from grok_bot.polymarket.client import ScriptedPolymarketClient, parse_market, slug_for_boundary
from grok_bot.polymarket.market_discovery import window_boundary


def test_window_boundary():
    assert window_boundary(300_000) == 300_000
    assert window_boundary(300_001) == 300_000


def test_slug():
    assert slug_for_boundary(300_000).startswith("btc-updown-5m-")


def test_scripted_book():
    from grok_bot.polymarket.market_discovery import MarketDescriptor

    m = MarketDescriptor("btc-updown-5m-300", "c", "up", "down", 300_000, 600_000)
    c = ScriptedPolymarketClient(m, up_mid=0.55)
    book = c.book("up")
    assert 0.54 < book.mid < 0.56


def test_parse_market():
    item = {
        "slug": "btc-updown-5m-1700000000",
        "conditionId": "abc",
        "clobTokenIds": '["tok_up","tok_down"]',
        "outcomes": '["Up","Down"]',
    }
    m = parse_market(item)
    assert m is not None
    assert m.up_token_id == "tok_up"