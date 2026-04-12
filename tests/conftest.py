from __future__ import annotations

from datetime import datetime

from tradingbot.config.settings import BotConfig


def make_bot_config(**overrides) -> BotConfig:
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
