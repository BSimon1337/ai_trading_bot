from __future__ import annotations

import logging
from dataclasses import replace

from tradingbot.config.settings import BotConfig
from tradingbot.execution.broker import build_alpaca_broker, build_trader
from tradingbot.execution.safeguards import RuntimeState

LOGGER = logging.getLogger(__name__)


def run_trading_loop(config: BotConfig, runtime_state: RuntimeState) -> None:
    from strategy import SentimentMLStrategy

    broker = build_alpaca_broker(config)
    trader = build_trader()
    for symbol in config.symbols:
        symbol_config = replace(config, symbol=symbol)
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
