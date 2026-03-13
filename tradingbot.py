from __future__ import annotations

import argparse
from dataclasses import replace
import logging
import os
from datetime import timedelta

from lumibot.traders import Trader

from backtester import run_backtest
from config import load_config
from strategy import SentimentMLStrategy
from utils import setup_logging

LOGGER = logging.getLogger(__name__)


def run_live() -> None:
    from lumibot.brokers import Alpaca

    config = load_config()
    if config.paper:
        LOGGER.info("PAPER_TRADING=true, running live loop in paper mode.")
    else:
        if os.getenv("ALLOW_LIVE_TRADING", "0") != "1":
            raise RuntimeError(
                "Live trading is blocked. Set ALLOW_LIVE_TRADING=1 only after paper-trading validation."
            )
        LOGGER.warning("Running with live funds. Confirm your Alpaca account permissions and limits.")

    broker = Alpaca(config.alpaca_creds)
    strategy = SentimentMLStrategy(
        name="sentiment_ml_strategy",
        broker=broker,
        parameters=config.strategy_parameters,
    )
    trader = Trader()
    trader.add_strategy(strategy)
    trader.run_all()


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Sentiment trading bot runner")
    parser.add_argument(
        "--mode",
        choices=["backtest", "live"],
        default="backtest",
        help="Run a historical backtest or start the live trading loop.",
    )
    parser.add_argument(
        "--quick-backtest",
        action="store_true",
        help="Run a shorter backtest window for fast feedback.",
    )
    parser.add_argument(
        "--quick-days",
        type=int,
        default=10,
        help="Number of days for --quick-backtest (default: 10).",
    )
    args = parser.parse_args()

    if args.mode == "backtest":
        config = load_config()
        if args.quick_backtest:
            quick_days = max(2, args.quick_days)
            quick_start = max(config.start_date, config.end_date - timedelta(days=quick_days))
            config = replace(config, start_date=quick_start)
            LOGGER.info(
                "Quick backtest enabled: %s to %s (%s days)",
                config.start_date.date(),
                config.end_date.date(),
                quick_days,
            )
        run_backtest(config, print_summary=args.quick_backtest)
    else:
        run_live()


if __name__ == "__main__":
    main()
