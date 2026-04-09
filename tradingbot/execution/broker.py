from __future__ import annotations

from tradingbot.config.settings import BotConfig


def build_alpaca_broker(config: BotConfig):
    from lumibot.brokers import Alpaca

    return Alpaca(config.alpaca_creds)


def build_trader():
    from lumibot.traders import Trader

    return Trader()
