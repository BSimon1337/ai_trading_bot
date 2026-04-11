from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from datetime import timedelta

from tradingbot.config.settings import BotConfig, load_config
from tradingbot.execution.logging import LogPaths, ensure_runtime_logs, log_run_event
from tradingbot.execution.safeguards import RuntimeGuardrailError, resolve_runtime_state
from utils import setup_logging

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
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
    return parser


def _run_backtest(config: BotConfig, quick_backtest: bool, quick_days: int) -> None:
    from backtester import run_backtest

    if quick_backtest:
        window_days = max(2, quick_days)
        quick_start = max(config.start_date, config.end_date - timedelta(days=window_days))
        config = replace(config, start_date=quick_start)
        LOGGER.info(
            "Quick backtest enabled: %s to %s (%s days)",
            config.start_date.date(),
            config.end_date.date(),
            window_days,
        )
    run_backtest(config, print_summary=quick_backtest)


def _run_live_loop(config: BotConfig, runtime_state=None) -> None:
    from tradingbot.app.live import run_trading_loop

    if runtime_state is None:
        runtime_state = resolve_runtime_state(config, "live")
    run_trading_loop(config, runtime_state)


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = _build_parser().parse_args(argv)
    config = load_config()

    if args.mode == "backtest":
        _run_backtest(config, quick_backtest=args.quick_backtest, quick_days=args.quick_days)
        return 0

    paths = LogPaths.from_config(config)
    ensure_runtime_logs(paths)
    try:
        runtime_state = resolve_runtime_state(config, args.mode)
    except RuntimeGuardrailError as exc:
        log_run_event(paths, mode="blocked-live", result="blocked", reason=str(exc))
        LOGGER.error(str(exc))
        return 2

    log_run_event(paths, mode=runtime_state.execution_mode, result="started", reason="runtime started")
    try:
        _run_live_loop(config, runtime_state)
    except Exception as exc:
        log_run_event(paths, mode=runtime_state.execution_mode, result="failed", reason=str(exc))
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
