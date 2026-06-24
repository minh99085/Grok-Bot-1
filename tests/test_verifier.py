from loop.verifier import verify_signal


def test_verifier_accepts_strong_signal():
    v = verify_signal({"sharpe": 2.0, "max_drawdown": 0.05, "newey_west_t": 2.5, "oos_years": 2.5})
    assert v.passed
    assert v.reasons == []


def test_verifier_rejects_weak_signal():
    v = verify_signal({"sharpe": 0.5, "max_drawdown": 0.20, "newey_west_t": 0.5, "oos_years": 0.5})
    assert not v.passed
    assert len(v.reasons) == 4