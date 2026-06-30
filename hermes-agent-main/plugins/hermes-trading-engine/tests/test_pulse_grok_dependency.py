"""Grok dependency screener validation."""

from __future__ import annotations

import json

from engine.pulse.grok_dependency import (
    parse_grok_dependency_response,
    validate_grok_proposals,
)
from engine.pulse.markets import OrderBook, PulseWindow  # noqa: F401 — used in _win


def test_parse_grok_json():
    raw = json.dumps({"proposals": [{
        "constraint_type": "nested_implication",
        "parent_window_key": "p",
        "child_window_keys": ["c"],
    }]})
    props = parse_grok_dependency_response(raw)
    assert len(props) == 1


def test_validate_rejects_unmapped():
    rep = validate_grok_proposals([{"constraint_type": "nested_implication",
                                      "parent_window_key": "x",
                                      "child_window_keys": ["y"]}],
                                    windows_by_id={})
    assert rep["deterministic_validated_dependencies"] == 0
    assert len(rep["rejected_dependencies"]) == 1


def _win(eid, ask=0.50, *, ws=300):
    return PulseWindow(
        event_id=eid, market_id="m", slug="s", title="t",
        open_ts=1e7, close_ts=1e7 + ws, up_token_id="U", down_token_id="D",
        window_seconds=ws, series_label="5m" if ws < 600 else "15m",
    )


def test_grok_conjunction_proposal_validates_with_two_children():
    parent = _win("p15", 0.10, ws=900)
    c1 = _win("c1", 0.60, ws=300)
    c2 = _win("c2", 0.58, ws=300)
    for w, ask in ((parent, 0.10), (c1, 0.60), (c2, 0.58)):
        w.up_book = OrderBook(best_bid=ask - 0.02, best_ask=ask,
                              asks=[(ask, 1000)], bids=[(ask - 0.02, 1000)])
    props = [{
        "constraint_type": "conjunction_implication",
        "parent_window_key": "p15",
        "child_window_keys": ["c1", "c2"],
        "description": "multi-child floor",
    }]
    rep = validate_grok_proposals(props, windows_by_id={
        "p15": parent, "c1": c1, "c2": c2,
    })
    assert rep["deterministic_validated_dependencies"] == 1
    assert rep["accepted_dependencies"][0]["constraint_type"] == "conjunction_implication"