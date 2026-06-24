"""Skill file loader — procedure manuals the loop reads each cycle."""

from __future__ import annotations

from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def read_skill(name: str) -> str:
    path = SKILLS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"skill not found: {name}")
    return path.read_text(encoding="utf-8")


def append_lesson(skill_name: str, lesson: str) -> None:
    """Append a confirmed lesson to the Lessons learned section."""
    path = SKILLS_DIR / f"{skill_name}.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Lessons learned"
    if marker not in text:
        text = text.rstrip() + f"\n\n{marker}\n"
    if not text.endswith("\n"):
        text += "\n"
    text += f"- {lesson}\n"
    path.write_text(text, encoding="utf-8")