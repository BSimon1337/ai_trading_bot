from __future__ import annotations

from dataclasses import dataclass

from tradingbot.config.settings import BotConfig


class RuntimeGuardrailError(RuntimeError):
    """Raised when a requested runtime mode violates execution safeguards."""


@dataclass(frozen=True)
class RuntimeState:
    requested_mode: str
    execution_mode: str
    paper: bool
    live_trading_enabled: bool
    confirmation_matched: bool


def resolve_runtime_state(config: BotConfig, requested_mode: str) -> RuntimeState:
    normalized_mode = requested_mode.strip().lower()
    if normalized_mode == "backtest":
        return RuntimeState(
            requested_mode=normalized_mode,
            execution_mode="backtest",
            paper=config.paper,
            live_trading_enabled=config.live_trading_enabled,
            confirmation_matched=False,
        )

    if config.paper and normalized_mode == "live":
        raise RuntimeGuardrailError("Live trading is blocked because PAPER_TRADING is enabled.")

    if config.paper:
        return RuntimeState(
            requested_mode=normalized_mode,
            execution_mode="paper",
            paper=True,
            live_trading_enabled=config.live_trading_enabled,
            confirmation_matched=False,
        )

    if not config.api_key or not config.api_secret:
        raise RuntimeGuardrailError("Live trading is blocked. Alpaca credentials are required.")

    confirmation_matched = config.live_run_confirmation == config.live_confirmation_token
    if not config.live_trading_enabled:
        raise RuntimeGuardrailError(
            "Live trading is blocked. Set LIVE_TRADING_ENABLED=1 only after paper validation."
        )
    if not confirmation_matched:
        raise RuntimeGuardrailError(
            "Live trading is blocked. Set LIVE_RUN_CONFIRMATION to the expected confirmation token for this run."
        )

    return RuntimeState(
        requested_mode=normalized_mode,
        execution_mode="live",
        paper=False,
        live_trading_enabled=True,
        confirmation_matched=True,
    )
