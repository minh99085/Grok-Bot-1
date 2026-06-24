"""Environment-backed configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str = "") -> str:
    return (os.getenv(name) or default).strip()


@dataclass(frozen=True)
class BotConfig:
    # Maker — Grok / xAI
    xai_api_key: str = ""
    xai_model: str = "grok-4.20-0309-non-reasoning"

    # Checker — Claude / Anthropic (independent verifier role)
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # TradingView BTCUSDT alert webhook
    tradingview_webhook_secret: str = ""
    tradingview_host: str = "127.0.0.1"
    tradingview_port: int = 8799
    tradingview_signals_path: str = "reports/tradingview_signals.jsonl"

    paper_only: bool = True

    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            xai_api_key=_env("XAI_API_KEY"),
            xai_model=_env("XAI_MODEL", "grok-4.20-0309-non-reasoning"),
            anthropic_api_key=_env("ANTHROPIC_API_KEY") or _env("CLAUDE_API_KEY"),
            claude_model=_env("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
            tradingview_webhook_secret=_env("TRADINGVIEW_WEBHOOK_SECRET"),
            tradingview_host=_env("TRADINGVIEW_HOST", "127.0.0.1"),
            tradingview_port=int(_env("TRADINGVIEW_PORT", "8799") or "8799"),
            tradingview_signals_path=_env(
                "TRADINGVIEW_SIGNALS_PATH", "reports/tradingview_signals.jsonl"
            ),
            paper_only=_env("PAPER_ONLY", "true").lower() in ("1", "true", "yes", "on"),
        )

    def llm_roles(self) -> dict[str, str]:
        return {
            "maker": "grok/xAI" if self.xai_api_key else "disabled",
            "checker": "claude/anthropic" if self.anthropic_api_key else "disabled",
        }