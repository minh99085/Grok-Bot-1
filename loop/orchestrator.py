"""Worktree orchestration for parallel strategy variants."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeSpec:
    name: str
    branch: str


def spawn_worktrees(
    repo_root: Path,
    specs: list[WorktreeSpec],
    *,
    base_dir: Path | None = None,
) -> list[Path]:
    """Create isolated git worktrees for parallel discovery workers."""
    parent = base_dir or (repo_root / "worktrees")
    parent.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for spec in specs:
        target = parent / spec.name
        if target.exists():
            created.append(target)
            continue
        subprocess.run(
            ["git", "worktree", "add", "-B", spec.branch, str(target)],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        created.append(target)
    return created


def n_trials_from_specs(specs: list[WorktreeSpec]) -> int:
    """Wire multiple-testing correction to actual variant count."""
    return max(1, len(specs))