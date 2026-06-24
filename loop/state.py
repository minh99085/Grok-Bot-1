"""State files: STATE.md (human) + state.json (machine) — the loop's memory."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_STATE_DIR = Path(__file__).resolve().parent / "state"


@dataclass
class LoopState:
    schema_version: int = 1
    windows_processed: int = 0
    current_rung: str = "observe"
    last_verdict: str = "pending"
    open_positions: list[dict[str, Any]] = field(default_factory=list)
    last_lesson_id: str | None = None
    kill_events: list[str] = field(default_factory=list)
    live_signoff: dict[str, Any] = field(
        default_factory=lambda: {"approved": False, "by": None, "at": None}
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class StateManager:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or DEFAULT_STATE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.json_path = self.root / "state.json"
        self.md_path = self.root / "STATE.md"

    def read(self) -> LoopState:
        if not self.json_path.exists():
            return LoopState()
        data = json.loads(self.json_path.read_text(encoding="utf-8"))
        return LoopState(**{k: v for k, v in data.items() if k in LoopState.__dataclass_fields__})

    def write(self, state: LoopState) -> None:
        state.updated_at = datetime.now(UTC).isoformat()
        self.json_path.write_text(
            json.dumps(state.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        self._write_md(state)

    def append_kill_event(self, message: str) -> LoopState:
        state = self.read()
        line = f"{datetime.now(UTC).isoformat()}: {message}"
        state.kill_events.append(line)
        self.write(state)
        return state

    def live_enabled(self) -> bool:
        state = self.read()
        return bool(state.live_signoff.get("approved"))

    def _write_md(self, state: LoopState) -> None:
        lines = [
            "# Grok-Bot-1 Loop State",
            "",
            f"- **Updated:** {state.updated_at}",
            f"- **Windows processed:** {state.windows_processed}",
            f"- **Promotion rung:** {state.current_rung}",
            f"- **Last verdict:** {state.last_verdict}",
            f"- **Open positions:** {len(state.open_positions)}",
            f"- **Last lesson:** {state.last_lesson_id or 'none'}",
            f"- **Live sign-off:** {state.live_signoff.get('approved', False)}",
            "",
        ]
        if state.kill_events:
            lines.append("## Kill events")
            lines.extend(f"- {e}" for e in state.kill_events[-20:])
            lines.append("")
        self.md_path.write_text("\n".join(lines), encoding="utf-8")