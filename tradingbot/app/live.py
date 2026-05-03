from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from tradingbot.config.settings import BotConfig
from tradingbot.execution.broker import build_alpaca_live_broker, build_alpaca_paper_broker, build_trader
from tradingbot.execution.safeguards import RuntimeState

LOGGER = logging.getLogger(__name__)


def _sanitize_symbol_for_path(symbol: str) -> str:
    return "".join(character for character in symbol.strip().lower() if character.isalnum())


def _symbol_log_root(symbol: str, *, mode: str) -> Path:
    suffix = "" if symbol.upper() == "SPY" else f"_{_sanitize_symbol_for_path(symbol)}"
    prefix = "paper_validation" if mode == "paper" else "live_validation"
    return Path("logs") / f"{prefix}{suffix}"


def _config_for_runtime_symbol(config: BotConfig, symbol: str, runtime_state: RuntimeState) -> BotConfig:
    if len(config.symbols) <= 1:
        return replace(config, symbol=symbol, symbols=(symbol,))
    root = _symbol_log_root(symbol, mode=runtime_state.execution_mode)
    return replace(
        config,
        symbol=symbol,
        symbols=(symbol,),
        decision_log_path=str(root / "decisions.csv"),
        fill_log_path=str(root / "fills.csv"),
        daily_snapshot_path=str(root / "daily_snapshot.csv"),
    )


def run_trading_loop(config: BotConfig, runtime_state: RuntimeState) -> None:
    from strategy import SentimentMLStrategy

    broker = build_alpaca_paper_broker(config) if runtime_state.paper else build_alpaca_live_broker(config)
    trader = build_trader()
    for symbol in config.symbols:
        symbol_config = _config_for_runtime_symbol(config, symbol, runtime_state)
        LOGGER.info(
            "Adding %s strategy for %s in %s mode",
            symbol_config.asset_class,
            symbol,
            runtime_state.execution_mode,
        )
        strategy = SentimentMLStrategy(
            name=f"sentiment_ml_{symbol.lower().replace('/', '_').replace('-', '_')}",
            broker=broker,
            parameters=symbol_config.strategy_parameters,
        )
        trader.add_strategy(strategy)
    trader.run_all()
