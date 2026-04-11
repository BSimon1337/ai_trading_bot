from __future__ import annotations

import logging
from typing import Any

from tradingbot.config.settings import BotConfig
from tradingbot.execution.logging import LogPaths, append_decision_record, ensure_runtime_logs
from utils import set_reproducible_seed, setup_logging, utc_now_string

LOGGER = logging.getLogger(__name__)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _record_backtest_summary(config: BotConfig, results: dict | None) -> None:
    paths = LogPaths.from_config(config)
    ensure_runtime_logs(paths)
    append_decision_record(
        paths,
        {
            "timestamp": utc_now_string(),
            "mode": "backtest",
            "symbol": config.symbol,
            "asset_class": config.asset_class,
            "action": "hold",
            "action_source": "backtest",
            "model_prob_up": "",
            "sentiment_probability": "",
            "sentiment_label": "",
            "quantity": 0,
            "portfolio_value": "",
            "cash": "",
            "reason": "backtest_completed" if results is not None else "backtest_no_results",
            "result": "completed" if results is not None else "skipped",
        },
    )


def run_backtest(config: BotConfig, print_summary: bool = False) -> dict | None:
    from lumibot.backtesting import YahooDataBacktesting
    from strategy import SentimentMLStrategy

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
        parameters={**config.strategy_parameters, "mode": "backtest"},
        show_plot=False,
        show_tearsheet=False,
        save_tearsheet=False,
        show_indicators=False,
    )
    _record_backtest_summary(config, results)

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
