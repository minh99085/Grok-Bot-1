"""Monte Carlo pricing engine: convergence to closed form, correlated dep-arb conditional, sizing."""

from __future__ import annotations

import pytest

from engine.pulse.monte_carlo import (
    HAVE_NUMPY, closed_form_digital_p_up, mc_digital_p_up,
    simulate_prices_at_times, mc_dependency_implication, pnl_summary,
)

pytestmark = pytest.mark.skipif(not HAVE_NUMPY, reason="numpy required for MC")


def test_mc_digital_converges_to_closed_form():
    sigma = 7e-5   # ~ realized per-sec vol seen live
    for s_now, s_open, secs in [(60000, 60000, 300), (60050, 60000, 300), (59950, 60000, 600)]:
        cf = closed_form_digital_p_up(s_now, s_open, sigma, secs)
        mc = mc_digital_p_up(s_now, s_open, sigma, secs, n_paths=60000, seed=7)
        assert abs(mc - cf) < 0.02, (s_now, s_open, secs, mc, cf)


def test_mc_digital_reproducible_with_seed():
    a = mc_digital_p_up(60010, 60000, 7e-5, 300, n_paths=20000, seed=42)
    b = mc_digital_p_up(60010, 60000, 7e-5, 300, n_paths=20000, seed=42)
    assert a == b


def test_jumps_widen_tails_move_probability():
    # With s_now above open, adding symmetric jumps pulls P(up) toward 0.5 (fatter tails).
    base = mc_digital_p_up(60200, 60000, 7e-5, 300, n_paths=60000, seed=3)
    withjumps = mc_digital_p_up(60200, 60000, 7e-5, 300, n_paths=60000, seed=3,
                                jump_intensity_per_sec=0.02, jump_sigma=0.002)
    assert withjumps < base  # fatter tails erode a modest directional lead


def test_shared_path_prices_shape_and_monotone_time():
    now = 1_000_000.0
    prices, idx = simulate_prices_at_times(60000, now, [now + 600, now + 300, now + 900],
                                           7e-5, n_paths=1000, rng=None)
    assert prices.shape == (1000, 3)
    assert set(idx.keys()) == {now + 300, now + 600, now + 900}
    assert idx[now + 300] < idx[now + 600] < idx[now + 900]


def test_dependency_conditional_lift_positive_when_child_nested_in_parent():
    now = 1_000_000.0
    parent = {"open_ts": now, "close_ts": now + 900, "s_open": 60000.0}
    child = {"open_ts": now + 300, "close_ts": now + 600}   # nested inside parent, future
    out = mc_dependency_implication(s_now=60000.0, now=now, parent=parent, children=[child],
                                    sigma_per_sec=7e-5, n_paths=40000, seed=11)
    assert out["available"] is True
    assert 0.0 <= out["p_parent_up_given_children_up"] <= 1.0
    # shared path => a child that rose makes the parent more likely to have risen
    assert out["implication_lift"] > 0.0


def test_dependency_adverse_selection_flag():
    now = 1_000_000.0
    parent = {"open_ts": now, "close_ts": now + 900, "s_open": 60000.0}
    child = {"open_ts": now + 300, "close_ts": now + 600}
    # expensive parent-UP entry -> conditional EV negative -> adverse selection True
    exp = mc_dependency_implication(s_now=60000.0, now=now, parent=parent, children=[child],
                                    sigma_per_sec=7e-5, entry_vwap=0.90, n_paths=40000, seed=5)
    assert exp["adverse_selection"] is True
    assert exp["ev_per_dollar_given_children_up"] < 0
    # cheap entry -> positive conditional EV -> not adverse
    cheap = mc_dependency_implication(s_now=60000.0, now=now, parent=parent, children=[child],
                                      sigma_per_sec=7e-5, entry_vwap=0.10, n_paths=40000, seed=5)
    assert cheap["adverse_selection"] is False
    assert cheap["ev_per_dollar_given_children_up"] > 0


def test_pnl_summary_kelly_and_loss_prob():
    s = pnl_summary(0.7, 0.5, size_usd=5.0, n_paths=40000, seed=9)
    assert s["kelly_fraction"] > 0            # +EV bet -> positive Kelly
    assert 0.25 < s["prob_loss"] < 0.35       # ~1 - p_win
    assert s["expected_pnl_usd"] > 0
    neg = pnl_summary(0.4, 0.5, n_paths=40000, seed=9)
    assert neg["kelly_fraction"] == 0.0       # -EV -> no bet
