"""Notify-only connector — pings operator on shadow/armed promotion."""

from __future__ import annotations

import json
import os
import urllib.request


def notify(message: str, *, level: str = "info") -> None:
    payload = {"text": f"[Grok-Bot-1:{level}] {message}"}
    print(json.dumps(payload))
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        return
    req = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=5)  # noqa: S310
    except Exception:
        pass  # notify-only; never block the loop