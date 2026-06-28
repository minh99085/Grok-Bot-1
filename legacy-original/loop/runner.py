"""Automation primitives: @loop (cadence) and @goal (until condition)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class LoopMeta:
    kind: str
    interval_seconds: float | None = None
    max_iterations: int = 10_000
    max_seconds: float = 86_400.0


def loop(
    *,
    interval_seconds: float,
    max_iterations: int = 10_000,
    max_seconds: float = 86_400.0,
) -> Callable[[F], F]:
    """Cadence trigger — reruns regardless of state."""

    def decorator(fn: F) -> F:
        fn._loop_meta = LoopMeta(  # type: ignore[attr-defined]
            kind="loop",
            interval_seconds=interval_seconds,
            max_iterations=max_iterations,
            max_seconds=max_seconds,
        )
        return fn

    return decorator


def goal(
    *,
    max_iterations: int = 1_000,
    max_seconds: float = 86_400.0,
) -> Callable[[F], F]:
    """Goal trigger — runs until condition_fn returns True."""

    def decorator(fn: F) -> F:
        fn._loop_meta = LoopMeta(  # type: ignore[attr-defined]
            kind="goal",
            max_iterations=max_iterations,
            max_seconds=max_seconds,
        )
        return fn

    return decorator


def run_loop(fn: Callable[[], Any], *, interval_seconds: float | None = None) -> int:
    meta: LoopMeta | None = getattr(fn, "_loop_meta", None)
    if interval_seconds is not None:
        every = interval_seconds
    elif meta and meta.interval_seconds is not None:
        every = meta.interval_seconds
    else:
        every = 60.0
    cap_iters = meta.max_iterations if meta else 10_000
    cap_secs = meta.max_seconds if meta else 86_400.0
    started = time.monotonic()
    iterations = 0
    while iterations < cap_iters and (time.monotonic() - started) < cap_secs:
        fn()
        iterations += 1
        time.sleep(every)
    return iterations


def run_goal(
    step: Callable[[int], Any],
    condition: Callable[[], bool],
    *,
    max_iterations: int = 1_000,
    max_seconds: float = 86_400.0,
) -> tuple[bool, int]:
    """Run step(i) until condition is True or caps hit. Condition is code-checked only."""
    started = time.monotonic()
    iterations = 0
    while iterations < max_iterations and (time.monotonic() - started) < max_seconds:
        if condition():
            return True, iterations
        step(iterations)
        iterations += 1
    return condition(), iterations