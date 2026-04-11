from __future__ import annotations

from tradingbot.config.settings import BotConfig


def build_alpaca_broker(config: BotConfig):
    from lumibot.brokers import Alpaca

    return Alpaca(config.alpaca_creds)


def build_alpaca_paper_broker(config: BotConfig):
    if not config.paper:
        raise ValueError("Paper broker requested while PAPER_TRADING is disabled.")
    return build_alpaca_broker(config)


def build_alpaca_live_broker(config: BotConfig):
    if config.paper:
        raise ValueError("Live broker requested while PAPER_TRADING is enabled.")
    return build_alpaca_broker(config)


def build_trader():
    from lumibot.traders import Trader

    return Trader()
