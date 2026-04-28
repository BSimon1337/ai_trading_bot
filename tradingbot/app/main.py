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
        choices=["backtest", "live", "preflight", "runtime-start"],
        default="backtest",
        help="Run a historical backtest or start the live trading loop.",
    )
    parser.add_argument(
        "--preflight-target",
        choices=["backtest", "paper", "live"],
        default=None,
        help="Runtime target to evaluate when --mode preflight is used.",
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
    parser.add_argument(
        "--managed-symbol",
        action="append",
        default=[],
        help="Symbol to start through the runtime manager. Can be supplied multiple times.",
    )
    return parser


def _run_backtest(config: BotConfig, quick_backtest: bool, quick_days: int) -> None:
    from tradingbot.app.backtest import run_backtest

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


def _run_runtime_manager_start(
    config: BotConfig,
    *,
    symbols: tuple[str, ...],
) -> int:
    from tradingbot.app.runtime_manager import start_managed_runtimes

    results = start_managed_runtimes(config, symbols, mode="live")
    for result in results:
        LOGGER.info(
            "Managed runtime start for %s -> %s (session=%s pid=%s)",
            result.symbol,
            result.runtime_state,
            result.session_id,
            result.pid,
        )
    return 0 if all(result.runtime_state == "running" for result in results) else 1


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = _build_parser().parse_args(argv)
    config = load_config()

    if args.mode == "backtest":
        _run_backtest(config, quick_backtest=args.quick_backtest, quick_days=args.quick_days)
        return 0

    if args.mode == "preflight":
        from tradingbot.app.preflight import run_preflight

        report = run_preflight(config, target_mode=args.preflight_target)
        output = report.to_text()
        print(output)
        paths = LogPaths.from_config(config)
        try:
            log_run_event(
                paths,
                mode=f"preflight-{args.preflight_target or ('paper' if config.paper else 'live')}",
                result=report.overall_status.value,
                reason=output.replace("\n", " | "),
            )
        except Exception as exc:
            LOGGER.warning("Unable to write preflight log event: %s", exc)
        return report.exit_code

    if args.mode == "runtime-start":
        symbols = tuple(args.managed_symbol) if args.managed_symbol else config.symbols
        return _run_runtime_manager_start(config, symbols=symbols)

    paths = LogPaths.from_config(config)
    ensure_runtime_logs(paths)
    try:
        runtime_state = resolve_runtime_state(config, args.mode)
    except RuntimeGuardrailError as exc:
        log_run_event(paths, mode="blocked-live", result="blocked", reason=str(exc))
        LOGGER.error(str(exc))
        return 2

    event_mode = "active-live" if runtime_state.execution_mode == "live" else runtime_state.execution_mode
    log_run_event(paths, mode=event_mode, result="started", reason="runtime started")
    try:
        _run_live_loop(config, runtime_state)
    except Exception as exc:
        log_run_event(paths, mode=event_mode, result="failed", reason=str(exc))
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
