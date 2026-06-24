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

    # Chainlink settlement (lagging oracle — not used as leading signal)
    eth_rpc_urls: str = ""
    chainlink_max_age_ms: int = 120_000
    cex_max_staleness_ms: int = 5000

    paper_only: bool = True

    # Read-only monitoring dashboard
    dashboard_host: str = "0.0.0.0"
    dashboard_port: int = 8800
    dashboard_token: str = ""
    dashboard_public_host: str = ""

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
            eth_rpc_urls=_env("ETH_RPC_URLS"),
            chainlink_max_age_ms=int(_env("CHAINLINK_MAX_AGE_MS", "120000") or "120000"),
            cex_max_staleness_ms=int(_env("CEX_MAX_STALENESS_MS", "5000") or "5000"),
            paper_only=_env("PAPER_ONLY", "true").lower() in ("1", "true", "yes", "on"),
            dashboard_host=_env("DASHBOARD_HOST", "0.0.0.0"),
            dashboard_port=int(_env("DASHBOARD_PORT", "8800") or "8800"),
            dashboard_token=_env("DASHBOARD_TOKEN"),
            dashboard_public_host=_env("DASHBOARD_PUBLIC_HOST"),
        )

    def llm_roles(self) -> dict[str, str]:
        return {
            "maker": "grok/xAI" if self.xai_api_key else "disabled",
            "checker": "claude/anthropic" if self.anthropic_api_key else "disabled",
        }