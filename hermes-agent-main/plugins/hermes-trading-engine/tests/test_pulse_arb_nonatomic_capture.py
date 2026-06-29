"""WS4 — cost-aware dutch-book capture: low epsilon + non-atomic sim as the per-opportunity filter.

Proves the operator-authorized 2026-06-29 change is HONEST, not phantom-edge:
- with a small fees-only epsilon, a genuine sub-$1 book that survives realistic leg-2 slippage is
  captured (actionable, guaranteed_profit > 0);
- a dust book whose edge is below the epsilon floor is NOT booked;
- a book that is atomically profitable but whose DOWN leg is too thin to survive impact + 50bps
  leg-2 slippage is rejected by the non-atomic sim (actionable when the sim is OFF, rejected when
  ON) — so we only ever book trades that stay guaranteed >= $0 under sequential fills.
"""

from __future__ import annotations

from engine.pulse.arbitrage import detect_arbitrage
from engine.pulse.markets import OrderBook

EPS = 0.003          # fees-only floor used live (apply-loop-arch-env.py)
NOW = 1000.0


def _book(asks, *, depth=100000.0):
    return OrderBook(best_bid=asks[0][0] - 0.05, best_ask=asks[0][0],
                     ask_depth_usd=depth, bid_depth_usd=depth, ts=NOW, asks=list(asks),
                     bids=[(asks[0][0] - 0.05, 100000.0)])


def _detect(up, dn, *, nonatomic):
    return detect_arbitrage(up, dn, fees=0.0, epsilon=EPS, max_usd=20.0,
                            max_depth_consume_frac=0.5, tick_size=0.01, now=NOW,
                            nonatomic_check=nonatomic, nonatomic_slippage_bps=50.0)


def test_genuine_subdollar_book_is_captured():
    up = _book([(0.49, 100000.0)])
    dn = _book([(0.49, 100000.0)])          # ask-sum 0.98 (2% edge), deep both legs
    opp = _detect(up, dn, nonatomic=True)
    assert opp is not None and opp.actionable is True
    assert opp.reason == "ok"
    assert opp.guaranteed_profit_usd > 0     # guaranteed >= $0 by construction


def test_dust_below_epsilon_not_booked():
    up = _book([(0.499, 100000.0)])
    dn = _book([(0.499, 100000.0)])          # ask-sum 0.998 -> 0.2% edge, below the 0.3% floor
    opp = _detect(up, dn, nonatomic=True)
    assert opp is None or opp.actionable is False
    if opp is not None:
        assert opp.reason == "below_epsilon"


def test_nonatomic_sim_rejects_thin_second_leg():
    # Atomically the pair looks profitable (VWAP-sum < 1), but the DOWN leg is thin: after filling
    # UP and impacting DOWN, the stressed leg-2 walks into a much worse level -> not risk-free.
    up = _book([(0.49, 100000.0)])
    dn = _book([(0.49, 40.0), (0.66, 100000.0)])   # only ~$19.6 at 0.49, then jumps to 0.66
    # sim OFF: atomic VWAP-sum < 1 -> looks actionable
    off = _detect(up, dn, nonatomic=False)
    assert off is not None and off.actionable is True
    # sim ON: impact + 50bps leg-2 slippage kills the edge -> rejected, never booked
    on = _detect(up, dn, nonatomic=True)
    assert on is not None and on.actionable is False
    assert on.reason.startswith("nonatomic")


def test_booked_profit_never_negative():
    for up_px, dn_px in ((0.49, 0.49), (0.48, 0.50), (0.45, 0.50)):
        opp = _detect(_book([(up_px, 100000.0)]), _book([(dn_px, 100000.0)]), nonatomic=True)
        if opp is not None and opp.actionable:
            assert opp.guaranteed_profit_usd >= 0.0
