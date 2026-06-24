"""Analyst proposes → verifier confirms → lesson staged → re-validated next cycle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loop.skills import append_lesson
from loop.verifier import verify_signal

# Thresholds the analyst may never auto-tune
FROZEN_KEYS = frozenset({"paper_only", "live_signoff", "min_oos_years"})


@dataclass(frozen=True)
class ProposedChange:
    skill_name: str
    lesson: str
    threshold_key: str
    new_value: float
    supporting_signal: dict[str, Any]


@dataclass(frozen=True)
class ReviewResult:
    approved: bool
    reason: str


def pre_check_change(change: ProposedChange, *, bounds: dict[str, tuple[float, float]]) -> ReviewResult:
    """Pure pre-check before any LLM reviewer runs."""
    if change.threshold_key in FROZEN_KEYS:
        return ReviewResult(False, f"{change.threshold_key} is not tunable")
    lo, hi = bounds.get(change.threshold_key, (0.0, 10.0))
    if not (lo <= change.new_value <= hi):
        return ReviewResult(False, f"{change.new_value} outside [{lo}, {hi}]")
    verdict = verify_signal(change.supporting_signal)
    if not verdict.passed:
        return ReviewResult(False, "supporting signal failed verifier")
    return ReviewResult(True, "pre_check passed")


def apply_confirmed_lesson(change: ProposedChange) -> None:
    """Write lesson to skill file. Threshold application happens after re-validation."""
    append_lesson(change.skill_name, change.lesson)


def dual_verify(
    change: ProposedChange,
    *,
    bounds: dict[str, tuple[float, float]] | None = None,
    reviewer_approves: bool,
) -> ReviewResult:
    """
    Maker proposes, checker confirms.
    reviewer_approves stands in for the independent LLM reviewer role.
    """
    pre = pre_check_change(change, bounds=bounds or {"min_sharpe": (1.0, 3.0)})
    if not pre.approved:
        return pre
    if not reviewer_approves:
        return ReviewResult(False, "independent reviewer rejected")
    apply_confirmed_lesson(change)
    return ReviewResult(True, "lesson appended; threshold staged for re-validation")