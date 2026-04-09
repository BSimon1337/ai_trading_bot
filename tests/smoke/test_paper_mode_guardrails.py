from __future__ import annotations

from datetime import datetime

from tradingbot.app import main as app_main
from tradingbot.config.settings import BotConfig


def _config(**overrides) -> BotConfig:
    defaults = dict(
        api_key="key",
        api_secret="secret",
        base_url="https://paper-api.alpaca.markets",
        paper=True,
        symbol="SPY",
        symbols=("SPY",),
        cash_at_risk=0.2,
        sentiment_probability_threshold=0.7,
        max_position_pct=0.25,
        max_gross_leverage=1.0,
        allow_short=False,
        daily_loss_limit_pct=0.03,
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31),
        slippage_bps=5.0,
        commission_per_share=0.0,
        random_seed=42,
        use_model_signal=True,
        model_path="models/xgb_full.joblib",
        model_long_threshold=0.55,
        kill_switch=False,
        max_trades_per_day=3,
        cooldown_minutes_after_loss=120,
        decision_log_path="logs/test/decisions.csv",
        fill_log_path="logs/test/fills.csv",
        daily_snapshot_path="logs/test/daily_snapshot.csv",
        max_notional_per_order_usd=10000.0,
        max_consecutive_losses=3,
        max_data_staleness_minutes=1440,
        live_trading_enabled=False,
        live_run_confirmation="",
        live_confirmation_token="CONFIRM",
    )
    defaults.update(overrides)
    return BotConfig(**defaults)


def test_live_command_runs_paper_mode_without_live_flags(monkeypatch):
    observed: dict[str, object] = {}

    monkeypatch.setattr(app_main, "setup_logging", lambda: None)
    monkeypatch.setattr(app_main, "load_config", lambda: _config(paper=True))
    monkeypatch.setattr(app_main, "ensure_runtime_logs", lambda paths: None)
    monkeypatch.setattr(app_main, "log_run_event", lambda paths, mode, result, reason: observed.update(mode=mode, result=result))
    monkeypatch.setattr(app_main, "_run_live_loop", lambda config: observed.update(ran=True, config=config))

    exit_code = app_main.main(["--mode", "live"])

    assert exit_code == 0
    assert observed["mode"] == "paper"
    assert observed["result"] == "started"
    assert observed["ran"] is True


def test_live_command_blocks_when_live_flags_missing(monkeypatch):
    observed: dict[str, object] = {}

    monkeypatch.setattr(app_main, "setup_logging", lambda: None)
    monkeypatch.setattr(app_main, "load_config", lambda: _config(paper=False, live_trading_enabled=False))
    monkeypatch.setattr(app_main, "ensure_runtime_logs", lambda paths: None)
    monkeypatch.setattr(
        app_main,
        "log_run_event",
        lambda paths, mode, result, reason: observed.update(mode=mode, result=result, reason=reason),
    )

    exit_code = app_main.main(["--mode", "live"])

    assert exit_code == 2
    assert observed["mode"] == "blocked-live"
    assert observed["result"] == "blocked"
    assert "LIVE_TRADING_ENABLED" in observed["reason"]
