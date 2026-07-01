"""Monte Carlo pricing engine for the BTC pulse (PAPER ONLY; deterministic CODE, not an LLM).

Design rationale (see quant-team analysis): our closed-form ``digital_p_up`` (Gaussian GBM digital
option) is exact, so MC of the same model just reproduces it. MC earns its keep only where a closed
form does not exist or the Gaussian assumption is wrong:

  * the CORRELATED multi-window dependency-arb joint distribution -- P(parent UP | all children UP)
    computed from ONE shared simulated BTC path per draw (the losing ``lcmm_nested`` lane implicitly
    assumed this ~= 1.0; MC prices the true conditional and exposes adverse selection),
  * fat-tail / jump return models vs the constant-sigma Gaussian,
  * a full P&L distribution for Kelly sizing + tail risk.

Vectorized with numpy; seedable + reproducible. This is the "code = simulator" layer: an LLM may
PARAMETERIZE it (distribution/drift/vol/scenarios) but the numbers are computed here, and the loop
grades them on real settled outcomes. Observe/advisory only -- never bypasses the execution floor.

numpy is imported lazily/guarded so a missing numpy can never break engine startup; callers should
check ``HAVE_NUMPY`` (or catch RuntimeError) and treat MC as unavailable if False.
"""

from __future__ import annotations

import math
from typing import Optional, Sequence

try:
    import numpy as np
    HAVE_NUMPY = True
except Exception:  # noqa: BLE001 — never break import if numpy is absent
    np = None  # type: ignore
    HAVE_NUMPY = False


def _require_numpy() -> None:
    if not HAVE_NUMPY:
        raise RuntimeError("monte_carlo requires numpy; MC unavailable")


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def closed_form_digital_p_up(s_now: float, s_open: float, sigma_per_sec: float,
                             r_seconds: float, *, mu_per_sec: float = 0.0) -> float:
    """The analytic reference (same model as engine.fair_value.digital_p_up): P(close >= open) for
    GBM. MC must converge to this for the plain Gaussian case."""
    if r_seconds <= 0 or sigma_per_sec <= 0 or s_now <= 0 or s_open <= 0:
        return 1.0 if s_now >= s_open else 0.0
    sig_h = sigma_per_sec * math.sqrt(r_seconds)
    z = (math.log(s_now / s_open) + (mu_per_sec - 0.5 * sigma_per_sec ** 2) * r_seconds) / sig_h
    return max(0.0, min(1.0, _norm_cdf(z)))


def _rng(seed: Optional[int]):
    return np.random.default_rng(seed)


def _terminal_log_returns(sigma_per_sec: float, seconds: float, n_paths: int, *,
                          mu_per_sec: float = 0.0, jump_intensity_per_sec: float = 0.0,
                          jump_sigma: float = 0.0, rng=None):
    """Terminal log-return over ``seconds`` for ``n_paths`` GBM draws, with optional compound-Poisson
    jumps (fat tails). Diffusion term: N((mu - 0.5 sigma^2) T, sigma^2 T)."""
    rng = rng if rng is not None else _rng(None)
    drift = (mu_per_sec - 0.5 * sigma_per_sec ** 2) * seconds
    diff = rng.normal(drift, sigma_per_sec * math.sqrt(seconds), size=n_paths)
    if jump_intensity_per_sec > 0.0 and jump_sigma > 0.0:
        n_jumps = rng.poisson(jump_intensity_per_sec * seconds, size=n_paths)
        # sum of n_jumps zero-mean normal jumps == N(0, n_jumps * jump_sigma^2)
        diff = diff + rng.normal(0.0, 1.0, size=n_paths) * (np.sqrt(n_jumps) * jump_sigma)
    return diff


def mc_digital_p_up(s_now: float, s_open: float, sigma_per_sec: float, r_seconds: float, *,
                    mu_per_sec: float = 0.0, n_paths: int = 20000, seed: Optional[int] = None,
                    jump_intensity_per_sec: float = 0.0, jump_sigma: float = 0.0) -> float:
    """MC estimate of P(close >= open). Converges to ``closed_form_digital_p_up`` for the pure
    Gaussian case; diverges (usefully) only when jumps/drift are supplied."""
    _require_numpy()
    if r_seconds <= 0 or sigma_per_sec <= 0:
        return 1.0 if s_now >= s_open else 0.0
    r = _terminal_log_returns(sigma_per_sec, r_seconds, int(n_paths), mu_per_sec=mu_per_sec,
                              jump_intensity_per_sec=jump_intensity_per_sec,
                              jump_sigma=jump_sigma, rng=_rng(seed))
    s_close = s_now * np.exp(r)
    return float(np.mean(s_close >= s_open))


def simulate_prices_at_times(s_now: float, now: float, times: Sequence[float],
                             sigma_per_sec: float, *, mu_per_sec: float = 0.0,
                             n_paths: int = 20000, rng=None,
                             jump_intensity_per_sec: float = 0.0, jump_sigma: float = 0.0):
    """Simulate correlated GBM prices at each future timestamp in ``times`` sharing ONE Brownian path
    per draw (this is what induces the cross-window correlation the dep-arb lane needs). Returns
    ``(prices[n_paths, k], {ts: col})`` for the sorted unique future ts."""
    _require_numpy()
    rng = rng if rng is not None else _rng(None)
    ts_sorted = sorted({float(t) for t in times if float(t) > now})
    if not ts_sorted:
        return np.empty((int(n_paths), 0)), {}
    prev = float(now)
    cum = np.zeros(int(n_paths))
    cols = []
    for t in ts_sorted:
        dt = max(1e-9, t - prev)
        drift = (mu_per_sec - 0.5 * sigma_per_sec ** 2) * dt
        step = rng.normal(drift, sigma_per_sec * math.sqrt(dt), size=int(n_paths))
        if jump_intensity_per_sec > 0.0 and jump_sigma > 0.0:
            nj = rng.poisson(jump_intensity_per_sec * dt, size=int(n_paths))
            step = step + rng.normal(0.0, 1.0, size=int(n_paths)) * (np.sqrt(nj) * jump_sigma)
        cum = cum + step
        cols.append(s_now * np.exp(cum))
        prev = t
    prices = np.stack(cols, axis=1)
    return prices, {t: i for i, t in enumerate(ts_sorted)}


def _window_open_close(win: dict, s_now: float, now: float, prices, idx: dict):
    """Return (open_price[n_paths], close_price[n_paths]) for a window. Observed opens (in the past
    with a known snapshot) are used as-is (leakage-free); future boundaries come from the sim."""
    n = None
    if prices is not None and getattr(prices, "shape", None):
        n = prices.shape[0]

    def _at(ts, observed):
        ts = float(ts)
        if ts <= now:
            base = float(observed) if observed is not None else float(s_now)
            return np.full(n if n else 1, base)
        return prices[:, idx[ts]]
    op = _at(win["open_ts"], win.get("s_open"))
    cp = _at(win["close_ts"], win.get("s_close"))
    return op, cp


def mc_dependency_implication(*, s_now: float, now: float, parent: dict, children: Sequence[dict],
                              sigma_per_sec: float, entry_vwap: Optional[float] = None,
                              mu_per_sec: float = 0.0, n_paths: int = 20000,
                              seed: Optional[int] = None,
                              jump_intensity_per_sec: float = 0.0, jump_sigma: float = 0.0) -> dict:
    """Price the CORRELATED dependency-arb joint distribution from one shared BTC path per draw.

    ``parent`` / each ``children[i]``: ``{"open_ts","close_ts","s_open"(optional observed)}``.
    Returns the true conditional ``p_parent_up_given_children_up`` -- the probability the nested
    "children UP => parent UP" implication actually pays. If ``entry_vwap`` (parent-UP price paid) is
    given, also returns the conditional EV and an adverse-selection flag (market priced it cheap but
    the conditional does not support it)."""
    _require_numpy()
    if sigma_per_sec <= 0:
        return {"available": False, "reason": "no_vol"}
    times = [parent["close_ts"]] + [c["close_ts"] for c in children]
    times += [parent["open_ts"]] + [c["open_ts"] for c in children]
    prices, idx = simulate_prices_at_times(
        s_now, now, times, sigma_per_sec, mu_per_sec=mu_per_sec, n_paths=int(n_paths),
        rng=_rng(seed), jump_intensity_per_sec=jump_intensity_per_sec, jump_sigma=jump_sigma)
    p_op, p_cp = _window_open_close(parent, s_now, now, prices, idx)
    parent_up = p_cp >= p_op
    children_up = np.ones(int(n_paths), dtype=bool)
    for c in children:
        c_op, c_cp = _window_open_close(c, s_now, now, prices, idx)
        children_up &= (c_cp >= c_op)
    n_children_up = int(children_up.sum())
    p_parent_up = float(parent_up.mean())
    p_children_all_up = float(children_up.mean())
    p_joint = float((parent_up & children_up).mean())
    p_cond = (p_joint / p_children_all_up) if p_children_all_up > 0 else None
    out = {
        "available": True, "n_paths": int(n_paths),
        "p_parent_up": round(p_parent_up, 4),
        "p_children_all_up": round(p_children_all_up, 4),
        "p_parent_up_given_children_up": (round(p_cond, 4) if p_cond is not None else None),
        "conditioning_samples": n_children_up,
        "implication_lift": (round(p_cond - p_parent_up, 4) if p_cond is not None else None),
    }
    if entry_vwap is not None and p_cond is not None:
        entry = float(entry_vwap)
        # buying parent-UP at `entry`: win -> (1-entry), lose -> -entry per $1 stake.
        ev_uncond = round(p_parent_up - entry, 4)
        ev_cond = round(p_cond - entry, 4)
        out.update({
            "entry_vwap": round(entry, 4),
            "ev_per_dollar_unconditional": ev_uncond,
            "ev_per_dollar_given_children_up": ev_cond,
            # adverse selection: the trade only fires when children are UP, so the CONDITIONAL EV is
            # what matters; flag when it is negative (market priced parent-UP above its true cond prob)
            "adverse_selection": bool(ev_cond < 0),
        })
    return out


def mc_should_veto(mc_result: Optional[dict], *, ev_threshold: float = -0.02) -> bool:
    """Gate decision: veto a dep-arb entry when the MC CONDITIONAL EV (the EV that actually applies,
    since the trade only fires when the children are UP) is clearly negative -- i.e. paying more for
    parent-UP than its true P(parent UP | children UP). Principled (negative-EV skip), not a guess."""
    if not mc_result or not mc_result.get("available"):
        return False
    ev = mc_result.get("ev_per_dollar_given_children_up")
    return ev is not None and float(ev) < float(ev_threshold)


class MCFlagGrader:
    """Grades the MC adverse-selection flag vs real settled outcomes so we can measure whether the
    flag actually predicts losses BEFORE trusting it to gate (precision/recall on 'flag => lost')."""

    def __init__(self):
        self.n = 0
        self.flagged = 0
        self.flagged_lost = 0            # flag said adverse AND parent-UP would have lost (true pos)
        self.not_flagged = 0
        self.not_flagged_won = 0          # not flagged AND parent-UP would have won (true neg)

    def record(self, *, flagged: bool, would_win: bool) -> None:
        self.n += 1
        if flagged:
            self.flagged += 1
            if not would_win:
                self.flagged_lost += 1
        else:
            self.not_flagged += 1
            if would_win:
                self.not_flagged_won += 1

    def report(self) -> dict:
        return {
            "graded": self.n, "flagged": self.flagged,
            "flag_precision": (round(self.flagged_lost / self.flagged, 4) if self.flagged else None),
            "not_flagged": self.not_flagged,
            "not_flagged_win_rate": (round(self.not_flagged_won / self.not_flagged, 4)
                                     if self.not_flagged else None),
            "note": "flag_precision = P(parent-UP would lose | MC flagged adverse); high => the veto "
                    "is correctly skipping losers.",
        }

    def to_state(self) -> dict:
        return {"n": self.n, "flagged": self.flagged, "flagged_lost": self.flagged_lost,
                "not_flagged": self.not_flagged, "not_flagged_won": self.not_flagged_won}

    def load_state(self, d: dict) -> None:
        if not d:
            return
        self.n = int(d.get("n", 0) or 0)
        self.flagged = int(d.get("flagged", 0) or 0)
        self.flagged_lost = int(d.get("flagged_lost", 0) or 0)
        self.not_flagged = int(d.get("not_flagged", 0) or 0)
        self.not_flagged_won = int(d.get("not_flagged_won", 0) or 0)


# ---- LLM-parameterized scenario (LLM = modeler; deterministic code = simulator) ---------------- #
NEUTRAL_SCENARIO = {"sigma_mult": 1.0, "mu_per_sec": 0.0, "jump_intensity_per_sec": 0.0,
                    "jump_sigma": 0.0, "source": "neutral"}

# Tight bounds so an LLM (esp. an anti-predictive one) can shade the model, never hijack it.
_SCENARIO_BOUNDS = {
    "sigma_mult": (0.5, 2.0), "mu_per_sec": (-5e-6, 5e-6),
    "jump_intensity_per_sec": (0.0, 0.05), "jump_sigma": (0.0, 0.01),
}


def validate_scenario_params(d, *, source: str = "llm") -> dict:
    """Clamp an LLM's proposed MC parameters into safe bounds; fall back to neutral on bad input.
    Keeps the LLM as a bounded *modeler* — it can tilt vol/drift/tail risk but not blow up the sim."""
    if not isinstance(d, dict):
        return dict(NEUTRAL_SCENARIO)
    out = {}
    for k, (lo, hi) in _SCENARIO_BOUNDS.items():
        try:
            v = float(d.get(k, NEUTRAL_SCENARIO[k]))
        except (TypeError, ValueError):
            v = NEUTRAL_SCENARIO[k]
        out[k] = max(lo, min(hi, v))
    out["source"] = str(d.get("source") or source)[:24]
    return out


def make_grok_scenario_fn(*, model: str = "grok-4.3", timeout_s: float = 15.0, chat=None):
    """Build ``fn(context) -> validated scenario params | None``. Asks the LLM to shade the MC's BTC
    return model for the next ~15 min from recent regime/news. Fail-open (None on any error)."""
    from engine.pulse.grok_intel import _grok_chat, _parse_json
    chat = chat if chat is not None else _grok_chat
    box: dict = {}

    def _fn(context: dict) -> Optional[dict]:
        prompt = (
            "You parameterize a Monte Carlo model of BTC's next ~15 minutes (base is Gaussian GBM). "
            "From the recent regime/news context, return factors to shade the model. STRICT JSON ONLY: "
            "{\"sigma_mult\":<0.5-2.0, vol vs realized>,\"mu_per_sec\":<-5e-6..5e-6 tiny drift>,"
            "\"jump_intensity_per_sec\":<0-0.05>,\"jump_sigma\":<0-0.01>}. Neutral = "
            "{sigma_mult:1,mu_per_sec:0,jump_intensity_per_sec:0,jump_sigma:0}. Only deviate on clear "
            "evidence.\nCONTEXT: " + str(context)[:2000])
        d = _parse_json(chat(prompt, model=model, timeout_s=timeout_s, box=box))
        if not isinstance(d, dict):
            return None
        return validate_scenario_params(d, source="grok")
    return _fn


class MCScenarioAdvisor:
    """Periodic LLM proposal of bounded MC scenario params, cached + fail-open to neutral. Runs on a
    background worker; the tick reads ``latest()`` (never blocks). PAPER; observe/advisory on params
    -- the MC still runs deterministically in code."""

    def __init__(self, *, scenario_fn=None, budget=None, context_fn=None,
                 interval_s: float = 300.0, max_age_s: float = 900.0, feature: str = "mc_scenario"):
        import threading
        import time as _t
        self._t = _t
        self._fn = scenario_fn if scenario_fn is not None else make_grok_scenario_fn()
        self._budget = budget
        self._context_fn = context_fn
        self.interval_s = max(60.0, float(interval_s))
        self.max_age_s = float(max_age_s)
        self.feature = feature
        self._lock = threading.Lock()
        self._params = dict(NEUTRAL_SCENARIO)
        self._ts = 0.0
        self.calls = 0
        self.errors = 0
        self.skipped_budget = 0
        self._stop = threading.Event()
        self._thread = None
        self._threading = threading

    def refresh(self) -> Optional[dict]:
        if self._budget is not None and not self._budget.try_spend(self.feature):
            self.skipped_budget += 1
            return None
        ctx = {}
        try:
            ctx = self._context_fn() if self._context_fn else {}
        except Exception:  # noqa: BLE001
            ctx = {}
        p = None
        try:
            p = self._fn(ctx)
        except Exception:  # noqa: BLE001
            p = None
        if p is None:
            self.errors += 1
        else:
            self.calls += 1
            with self._lock:
                self._params, self._ts = validate_scenario_params(p, source=p.get("source", "llm")), self._t.time()
        return p

    def latest(self) -> dict:
        with self._lock:
            if self._ts and (self._t.time() - self._ts) <= self.max_age_s:
                return dict(self._params)
        return dict(NEUTRAL_SCENARIO)

    def _worker(self) -> None:
        self._stop.wait(min(self.interval_s, 20.0))
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception:  # noqa: BLE001
                pass
            self._stop.wait(self.interval_s)

    def start(self) -> "MCScenarioAdvisor":
        if self._thread is None or not self._thread.is_alive():
            self._stop.clear()
            self._thread = self._threading.Thread(target=self._worker, name="mc-scenario", daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()

    def report(self) -> dict:
        with self._lock:
            return {"enabled": True, "calls": self.calls, "errors": self.errors,
                    "skipped_budget": self.skipped_budget, "params": dict(self._params),
                    "age_s": (round(self._t.time() - self._ts, 1) if self._ts else None)}


def pnl_summary(prob_win: float, entry_price: float, *, size_usd: float = 1.0,
                n_paths: int = 20000, seed: Optional[int] = None) -> dict:
    """Full P&L distribution + Kelly for a single binary payoff bought at ``entry_price``.
    win -> +(1-entry)*shares ; lose -> -entry*shares, shares = size_usd/entry."""
    _require_numpy()
    p = max(0.0, min(1.0, float(prob_win)))
    entry = min(0.999, max(1e-6, float(entry_price)))
    shares = float(size_usd) / entry
    wins = _rng(seed).random(int(n_paths)) < p
    pnl = np.where(wins, (1.0 - entry) * shares, -entry * shares)
    b = (1.0 - entry) / entry                       # net odds
    kelly = (p * (b + 1.0) - 1.0) / b if b > 0 else 0.0
    return {
        "prob_win": round(p, 4), "entry_price": round(entry, 4),
        "expected_pnl_usd": round(float(pnl.mean()), 4),
        "std_pnl_usd": round(float(pnl.std()), 4),
        "q05_pnl_usd": round(float(np.quantile(pnl, 0.05)), 4),
        "median_pnl_usd": round(float(np.quantile(pnl, 0.50)), 4),
        "q95_pnl_usd": round(float(np.quantile(pnl, 0.95)), 4),
        "prob_loss": round(float((pnl < 0).mean()), 4),
        "kelly_fraction": round(max(0.0, min(1.0, kelly)), 4),
    }
