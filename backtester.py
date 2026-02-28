from __future__ import annotations

import logging
from typing import Any

from lumibot.backtesting import YahooDataBacktesting

from config import BotConfig, load_config
from strategy import SentimentMLStrategy
from utils import set_reproducible_seed, setup_logging, utc_now_string

LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def run_backtest(config: BotConfig, print_summary: bool = False) -> dict | None:
    setup_logging()
    set_reproducible_seed(config.random_seed)
    LOGGER.info("Starting backtest at %s", utc_now_string())
    LOGGER.info("Symbol=%s Start=%s End=%s", config.symbol, config.start_date, config.end_date)
    LOGGER.info(
        "Risk limits: position<=%.0f%% gross_leverage<=%.2f short=%s daily_loss<=%.0f%%",
        config.max_position_pct * 100.0,
        config.max_gross_leverage,
        config.allow_short,
        config.daily_loss_limit_pct * 100.0,
    )
    LOGGER.info(
        "Execution assumptions: slippage_bps=%.2f commission_per_share=%.4f",
        config.slippage_bps,
        config.commission_per_share,
    )

    results, strategy = SentimentMLStrategy.run_backtest(
        YahooDataBacktesting,
        config.start_date,
        config.end_date,
        parameters=config.strategy_parameters,
        show_plot=False,
        show_tearsheet=False,
        save_tearsheet=False,
        show_indicators=False,
    )

    if print_summary:
        stats = getattr(strategy, "_stats", None)
        start_value = 0.0
        end_value = 0.0
        if stats is not None and not stats.empty and "portfolio_value" in stats.columns:
            start_value = _safe_float(stats["portfolio_value"].iloc[0])
            end_value = _safe_float(stats["portfolio_value"].iloc[-1])
        total_return_pct = _safe_float(results.get("total_return", 0.0)) * 100.0
        sharpe = _safe_float(results.get("sharpe", 0.0))
        cagr_pct = _safe_float(results.get("cagr", 0.0)) * 100.0
        max_dd = results.get("max_drawdown", {})
        max_dd_pct = _safe_float(max_dd.get("drawdown", 0.0)) * 100.0 if isinstance(max_dd, dict) else 0.0
        trade_log_df = getattr(strategy.broker, "_trade_event_log_df", None)
        trade_events = 0 if trade_log_df is None else int(len(trade_log_df))

        print("\n=== Quick Backtest Summary ===")
        print(f"Symbol: {config.symbol}")
        print(f"Window: {config.start_date.date()} -> {config.end_date.date()}")
        print(f"Start Value: ${start_value:,.2f}")
        print(f"End Value:   ${end_value:,.2f}")
        print(f"Total Return: {total_return_pct:.2f}%")
        print(f"CAGR: {cagr_pct:.2f}%")
        print(f"Sharpe: {sharpe:.2f}")
        print(f"Max Drawdown: {max_dd_pct:.2f}%")
        print(f"Trade Events: {trade_events}")
        print("================================\n")

    return results


if __name__ == "__main__":
    run_backtest(load_config(), print_summary=True)
