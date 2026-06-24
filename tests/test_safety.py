import pytest

from grok_bot.safety import LiveTradingDisabledError, submit_order


def test_paper_fill():
    fill = submit_order({"name": "x", "notional": 50, "edge": 0.1}, paper=True)
    assert fill["paper"] is True
    assert fill["pnl"] == 5.0


def test_live_raises():
    with pytest.raises(LiveTradingDisabledError):
        submit_order({"name": "x"}, paper=False)