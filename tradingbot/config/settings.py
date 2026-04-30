from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tradingbot.config.crypto_universe import (
    crypto_universe_symbols,
    dedupe_symbols,
    normalize_crypto_symbol,
)

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in bare environments
    def load_dotenv(*args, **kwargs) -> bool:
        return False


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


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _get_symbols() -> tuple[str, ...]:
    symbols: list[str] = []
    raw = os.getenv("SYMBOLS", "").strip()
    if raw:
        symbols.extend(normalize_crypto_symbol(symbol) for symbol in raw.split(",") if symbol.strip())
    else:
        symbols.append(os.getenv("SYMBOL", "SPY").strip().upper())

    crypto_raw = os.getenv("CRYPTO_SYMBOLS", "").strip()
    if crypto_raw:
        symbols.extend(
            normalize_crypto_symbol(symbol)
            for symbol in crypto_raw.split(",")
            if symbol.strip()
        )

    universe = os.getenv("ALPACA_CRYPTO_UNIVERSE", "none").strip()
    symbols.extend(crypto_universe_symbols(universe))
    return dedupe_symbols(symbols)


def infer_asset_class(symbol: str) -> str:
    normalized = normalize_crypto_symbol(symbol)
    if "/" in normalized:
        return "crypto"
    if normalized.endswith("USD") and len(normalized) > 3:
        return "crypto"
    return "stock"


@dataclass(frozen=True)
class BotConfig:
    api_key: str
    api_secret: str
    base_url: str
    paper: bool
    symbol: str
    symbols: tuple[str, ...]
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
    max_notional_per_order_usd: float
    max_consecutive_losses: int
    max_data_staleness_minutes: int
    live_trading_enabled: bool
    live_run_confirmation: str
    live_confirmation_token: str
    runtime_registry_path: str = "logs/runtime/runtime_registry.json"
    runtime_recent_sessions_limit: int = 25
    runtime_recent_control_actions_limit: int = 25
    offline_news_enabled: bool = False
    offline_news_dir: str = "data/offline_news"

    @property
    def alpaca_creds(self) -> dict[str, object]:
        return {
            "API_KEY": self.api_key,
            "API_SECRET": self.api_secret,
            "PAPER": self.paper,
        }

    @property
    def log_paths(self) -> dict[str, Path]:
        return {
            "decisions": Path(self.decision_log_path),
            "fills": Path(self.fill_log_path),
            "snapshot": Path(self.daily_snapshot_path),
        }

    @property
    def asset_class(self) -> str:
        return infer_asset_class(self.symbol)

    @property
    def asset_classes(self) -> dict[str, str]:
        return {symbol: infer_asset_class(symbol) for symbol in self.symbols}

    @property
    def strategy_parameters(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "mode": "paper" if self.paper else "live",
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
            "max_notional_per_order_usd": self.max_notional_per_order_usd,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_data_staleness_minutes": self.max_data_staleness_minutes,
            "offline_news_enabled": self.offline_news_enabled,
            "offline_news_dir": self.offline_news_dir,
        }


def load_config() -> BotConfig:
    _load_env_files()

    api_key = os.getenv("API_KEY", os.getenv("ALPACA_API_KEY", "")).strip()
    api_secret = os.getenv("API_SECRET", os.getenv("ALPACA_API_SECRET", "")).strip()
    base_url = os.getenv("BASE_URL", "https://paper-api.alpaca.markets").strip()
    if not api_key or not api_secret:
        raise ValueError(
            "Missing Alpaca credentials. Set API_KEY/API_SECRET (or ALPACA_API_KEY/ALPACA_API_SECRET)."
        )

    start_date = datetime.strptime(os.getenv("BACKTEST_START", "2020-01-01"), "%Y-%m-%d")
    end_date = datetime.strptime(os.getenv("BACKTEST_END", "2024-11-01"), "%Y-%m-%d")
    if start_date >= end_date:
        raise ValueError("BACKTEST_START must be earlier than BACKTEST_END.")

    symbols = _get_symbols()
    paper = _get_bool("PAPER_TRADING", True)
    live_enabled = _get_bool("LIVE_TRADING_ENABLED", _get_bool("ALLOW_LIVE_TRADING", False))

    return BotConfig(
        api_key=api_key,
        api_secret=api_secret,
        base_url=base_url,
        paper=paper,
        symbol=symbols[0],
        symbols=symbols,
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
        random_seed=_get_int("RANDOM_SEED", 42),
        use_model_signal=_get_bool("USE_MODEL_SIGNAL", True),
        model_path=os.getenv("MODEL_PATH", "models/xgb_full.joblib"),
        model_long_threshold=_get_float("MODEL_LONG_THRESHOLD", 0.55),
        kill_switch=_get_bool("KILL_SWITCH", False),
        max_trades_per_day=_get_int("MAX_TRADES_PER_DAY", 3),
        cooldown_minutes_after_loss=_get_int("COOLDOWN_MINUTES_AFTER_LOSS", 120),
        decision_log_path=os.getenv("DECISION_LOG_PATH", "logs/paper_validation/decisions.csv"),
        fill_log_path=os.getenv("FILL_LOG_PATH", "logs/paper_validation/fills.csv"),
        daily_snapshot_path=os.getenv("DAILY_SNAPSHOT_PATH", "logs/paper_validation/daily_snapshot.csv"),
        max_notional_per_order_usd=_get_float("MAX_NOTIONAL_PER_ORDER_USD", 10000.0),
        max_consecutive_losses=_get_int("MAX_CONSECUTIVE_LOSSES", 3),
        max_data_staleness_minutes=_get_int("MAX_DATA_STALENESS_MINUTES", 1440),
        live_trading_enabled=live_enabled,
        live_run_confirmation=os.getenv("LIVE_RUN_CONFIRMATION", "").strip(),
        live_confirmation_token=os.getenv("LIVE_CONFIRMATION_TOKEN", "CONFIRM").strip() or "CONFIRM",
        runtime_registry_path=os.getenv("RUNTIME_REGISTRY_PATH", "logs/runtime/runtime_registry.json").strip()
        or "logs/runtime/runtime_registry.json",
        runtime_recent_sessions_limit=_get_int("RUNTIME_RECENT_SESSIONS_LIMIT", 25),
        runtime_recent_control_actions_limit=_get_int("RUNTIME_RECENT_CONTROL_ACTIONS_LIMIT", 25),
        offline_news_enabled=_get_bool("OFFLINE_NEWS_ENABLED", False),
        offline_news_dir=os.getenv("OFFLINE_NEWS_DIR", "data/offline_news").strip() or "data/offline_news",
    )
