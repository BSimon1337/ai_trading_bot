from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv


def _load_env_files() -> None:
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path="env/.env", override=False)


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


@dataclass(frozen=True)
class BotConfig:
    api_key: str
    api_secret: str
    base_url: str
    paper: bool
    symbol: str
    cash_at_risk: float
    sentiment_probability_threshold: float
    max_position_pct: float
    max_gross_leverage: float
    allow_short: bool
    daily_loss_limit_pct: float
    start_date: datetime
    end_date: datetime
    slippage_bps: float
    commission_per_share: float
    random_seed: int
    use_model_signal: bool
    model_path: str
    model_long_threshold: float
    kill_switch: bool
    max_trades_per_day: int
    cooldown_minutes_after_loss: int
    decision_log_path: str
    fill_log_path: str
    daily_snapshot_path: str

    @property
    def alpaca_creds(self) -> dict:
        return {
            "API_KEY": self.api_key,
            "API_SECRET": self.api_secret,
            "PAPER": self.paper,
        }

    @property
    def strategy_parameters(self) -> dict:
        return {
            "symbol": self.symbol,
            "cash_at_risk": self.cash_at_risk,
            "sentiment_probability_threshold": self.sentiment_probability_threshold,
            "max_position_pct": self.max_position_pct,
            "max_gross_leverage": self.max_gross_leverage,
            "allow_short": self.allow_short,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "slippage_bps": self.slippage_bps,
            "commission_per_share": self.commission_per_share,
            "use_model_signal": self.use_model_signal,
            "model_path": self.model_path,
            "model_long_threshold": self.model_long_threshold,
            "kill_switch": self.kill_switch,
            "max_trades_per_day": self.max_trades_per_day,
            "cooldown_minutes_after_loss": self.cooldown_minutes_after_loss,
            "decision_log_path": self.decision_log_path,
            "fill_log_path": self.fill_log_path,
            "daily_snapshot_path": self.daily_snapshot_path,
        }


def load_config() -> BotConfig:
    _load_env_files()

    api_key = os.getenv("API_KEY", os.getenv("ALPACA_API_KEY", ""))
    api_secret = os.getenv("API_SECRET", os.getenv("ALPACA_API_SECRET", ""))
    base_url = os.getenv("BASE_URL", "https://paper-api.alpaca.markets")

    if not api_key or not api_secret:
        raise ValueError(
            "Missing Alpaca credentials. Set API_KEY/API_SECRET (or ALPACA_API_KEY/ALPACA_API_SECRET)."
        )

    start_date = datetime.strptime(os.getenv("BACKTEST_START", "2020-01-01"), "%Y-%m-%d")
    end_date = datetime.strptime(os.getenv("BACKTEST_END", "2024-11-01"), "%Y-%m-%d")
    if start_date >= end_date:
        raise ValueError("BACKTEST_START must be earlier than BACKTEST_END.")

    return BotConfig(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        paper=_get_bool("PAPER_TRADING", True),
        symbol=os.getenv("SYMBOL", "SPY"),
        cash_at_risk=_get_float("CASH_AT_RISK", 0.20),
        sentiment_probability_threshold=_get_float("SENTIMENT_THRESHOLD", 0.70),
        max_position_pct=_get_float("MAX_POSITION_PCT", 0.25),
        max_gross_leverage=_get_float("MAX_GROSS_LEVERAGE", 1.00),
        allow_short=_get_bool("ALLOW_SHORT", False),
        daily_loss_limit_pct=_get_float("DAILY_LOSS_LIMIT_PCT", 0.03),
        start_date=start_date,
        end_date=end_date,
        slippage_bps=_get_float("SLIPPAGE_BPS", 5.0),
        commission_per_share=_get_float("COMMISSION_PER_SHARE", 0.0),
        random_seed=int(os.getenv("RANDOM_SEED", "42")),
        use_model_signal=_get_bool("USE_MODEL_SIGNAL", True),
        model_path=os.getenv("MODEL_PATH", "models/xgb_full.joblib"),
        model_long_threshold=_get_float("MODEL_LONG_THRESHOLD", 0.55),
        kill_switch=_get_bool("KILL_SWITCH", False),
        max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "3")),
        cooldown_minutes_after_loss=int(os.getenv("COOLDOWN_MINUTES_AFTER_LOSS", "120")),
        decision_log_path=os.getenv("DECISION_LOG_PATH", "logs/paper_validation/decisions.csv"),
        fill_log_path=os.getenv("FILL_LOG_PATH", "logs/paper_validation/fills.csv"),
        daily_snapshot_path=os.getenv("DAILY_SNAPSHOT_PATH", "logs/paper_validation/daily_snapshot.csv"),
    )
