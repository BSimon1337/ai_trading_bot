from __future__ import annotations

from tradingbot.app.live import _config_for_runtime_symbol
from tradingbot.execution.safeguards import RuntimeState
from tests.conftest import make_bot_config


def _runtime_state(mode: str) -> RuntimeState:
    return RuntimeState(
        requested_mode=mode,
        execution_mode=mode,
        paper=mode == "paper",
        live_trading_enabled=mode == "live",
        confirmation_matched=mode == "live",
    )


def test_multi_symbol_live_loop_uses_symbol_scoped_live_log_paths():
    config = make_bot_config(
        paper=False,
        symbols=("SPY", "ETH/USD"),
        decision_log_path="logs/live_validation/decisions.csv",
        fill_log_path="logs/live_validation/fills.csv",
        daily_snapshot_path="logs/live_validation/daily_snapshot.csv",
    )

    symbol_config = _config_for_runtime_symbol(config, "ETH/USD", _runtime_state("live"))

    assert symbol_config.symbols == ("ETH/USD",)
    assert symbol_config.decision_log_path.endswith("live_validation_ethusd\\decisions.csv") or symbol_config.decision_log_path.endswith(
        "live_validation_ethusd/decisions.csv"
    )
    assert symbol_config.fill_log_path.endswith("live_validation_ethusd\\fills.csv") or symbol_config.fill_log_path.endswith(
        "live_validation_ethusd/fills.csv"
    )
    assert symbol_config.daily_snapshot_path.endswith("live_validation_ethusd\\daily_snapshot.csv") or symbol_config.daily_snapshot_path.endswith(
        "live_validation_ethusd/daily_snapshot.csv"
    )


def test_single_symbol_live_loop_preserves_configured_log_paths():
    config = make_bot_config(
        paper=False,
        symbols=("ETH/USD",),
        decision_log_path="custom/decisions.csv",
        fill_log_path="custom/fills.csv",
        daily_snapshot_path="custom/snapshot.csv",
    )

    symbol_config = _config_for_runtime_symbol(config, "ETH/USD", _runtime_state("live"))

    assert symbol_config.decision_log_path == "custom/decisions.csv"
    assert symbol_config.fill_log_path == "custom/fills.csv"
    assert symbol_config.daily_snapshot_path == "custom/snapshot.csv"
