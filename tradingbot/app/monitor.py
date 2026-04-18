from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from tradingbot.config.settings import BotConfig, infer_asset_class


DEFAULT_REFRESH_SECONDS = 15
DEFAULT_STALE_AFTER_MINUTES = 180
SENSITIVE_KEYWORDS = ("key", "secret", "token", "password", "credential")


@dataclass(frozen=True)
class RuntimeStatus:
    state: str
    severity: str
    message: str
    age_minutes: float | None = None


@dataclass(frozen=True)
class DecisionSummary:
    timestamp: str = ""
    mode: str = ""
    symbol: str = ""
    asset_class: str = ""
    action: str = ""
    action_source: str = ""
    model_prob_up: str = ""
    sentiment_source: str = ""
    sentiment_probability: str = ""
    sentiment_label: str = ""
    quantity: str = ""
    portfolio_value: str = ""
    cash: str = ""
    reason: str = ""
    result: str = ""


@dataclass(frozen=True)
class FillSummary:
    timestamp: str = ""
    mode: str = ""
    symbol: str = ""
    asset_class: str = ""
    side: str = ""
    quantity: str = ""
    order_id: str = ""
    portfolio_value: str = ""
    cash: str = ""
    notional_usd: str = ""
    result: str = ""


@dataclass(frozen=True)
class SnapshotSummary:
    date: str = ""
    mode: str = ""
    symbol: str = ""
    portfolio_value: str = ""
    cash: str = ""
    position_qty: str = ""
    day_pnl: str = ""


@dataclass(frozen=True)
class IssueSummary:
    timestamp: str
    severity: str
    symbol: str
    category: str
    message: str
    source: str


@dataclass(frozen=True)
class DashboardInstance:
    label: str
    symbols: tuple[str, ...]
    asset_classes: tuple[str, ...]
    decision_log_path: Path
    fill_log_path: Path
    snapshot_log_path: Path
    status: RuntimeStatus = field(
        default_factory=lambda: RuntimeStatus("no_data", "warning", "No runtime evidence found.")
    )
    last_updated_at: str | None = None
    latest_decision: DecisionSummary | None = None
    latest_fill: FillSummary | None = None
    latest_snapshot: SnapshotSummary | None = None
    issues: tuple[IssueSummary, ...] = ()


@dataclass(frozen=True)
class MonitorConfiguration:
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    tray_enabled: bool = True
    read_only: bool = True
    instances: tuple[DashboardInstance, ...] = ()


@dataclass(frozen=True)
class TrayState:
    label: str = "AI Trading Bot Monitor"
    state: str = "unavailable"
    tooltip: str = "Monitor is not running."
    last_updated_at: str | None = None
    menu_actions: tuple[str, ...] = ("Open Dashboard", "Refresh Status", "Exit Monitor")


@dataclass(frozen=True)
class CsvReadResult:
    path: Path
    dataframe: pd.DataFrame
    issue: IssueSummary | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def safe_read_csv(path: Path, source: str = "csv") -> CsvReadResult:
    path = Path(path)
    if not path.exists():
        return CsvReadResult(
            path=path,
            dataframe=pd.DataFrame(),
            issue=IssueSummary(
                timestamp=_utc_now_iso(),
                severity="warning",
                symbol="SYSTEM",
                category="no_data",
                message=f"Runtime evidence file does not exist: {path}",
                source=source,
            ),
        )
    try:
        return CsvReadResult(path=path, dataframe=pd.read_csv(path))
    except Exception as exc:
        return CsvReadResult(
            path=path,
            dataframe=pd.DataFrame(),
            issue=IssueSummary(
                timestamp=_utc_now_iso(),
                severity="warning",
                symbol="SYSTEM",
                category="malformed_csv",
                message=f"Could not read runtime evidence file {path}: {exc}",
                source=source,
            ),
        )


def normalize_timestamps(dataframe: pd.DataFrame, column: str = "timestamp") -> pd.DataFrame:
    if dataframe.empty or column not in dataframe.columns:
        return dataframe
    normalized = dataframe.copy()
    normalized[column] = pd.to_datetime(normalized[column], errors="coerce", utc=True)
    return normalized.sort_values(column)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sanitize_symbol_for_path(symbol: str) -> str:
    normalized = symbol.strip().lower()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _paths_for_symbol(symbol: str, base_dir: Path = Path("logs")) -> tuple[Path, Path, Path]:
    suffix = "" if symbol.upper() == "SPY" else f"_{sanitize_symbol_for_path(symbol)}"
    root = base_dir / f"paper_validation{suffix}"
    return root / "decisions.csv", root / "fills.csv", root / "daily_snapshot.csv"


def discover_monitor_instances(
    config: BotConfig | None = None,
    symbols: tuple[str, ...] | None = None,
    base_dir: Path = Path("logs"),
) -> tuple[DashboardInstance, ...]:
    if symbols is None and config is not None:
        symbols = config.symbols
    if symbols is None:
        env_symbols = tuple(symbol.strip().upper() for symbol in os.getenv("SYMBOLS", "").split(",") if symbol.strip())
        symbols = env_symbols or ("SPY", "BTC/USD")

    instances: list[DashboardInstance] = []
    for index, symbol in enumerate(symbols):
        if config is not None and len(symbols) == 1 and index == 0:
            decision_path = Path(config.decision_log_path)
            fill_path = Path(config.fill_log_path)
            snapshot_path = Path(config.daily_snapshot_path)
        else:
            decision_path, fill_path, snapshot_path = _paths_for_symbol(symbol, base_dir=base_dir)
        instances.append(
            DashboardInstance(
                label=symbol,
                symbols=(symbol,),
                asset_classes=(infer_asset_class(symbol),),
                decision_log_path=decision_path,
                fill_log_path=fill_path,
                snapshot_log_path=snapshot_path,
            )
        )
    return tuple(instances)


def load_monitor_configuration(
    config: BotConfig | None = None,
    *,
    symbols: tuple[str, ...] | None = None,
    base_dir: Path = Path("logs"),
) -> MonitorConfiguration:
    refresh_seconds = _safe_int(os.getenv("MONITOR_REFRESH_SECONDS"), DEFAULT_REFRESH_SECONDS)
    dashboard_port = _safe_int(os.getenv("MONITOR_PORT"), 8080)
    dashboard_host = os.getenv("MONITOR_HOST", "127.0.0.1").strip() or "127.0.0.1"
    tray_enabled = os.getenv("MONITOR_TRAY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
    return MonitorConfiguration(
        dashboard_host=dashboard_host,
        dashboard_port=dashboard_port,
        refresh_seconds=refresh_seconds,
        tray_enabled=tray_enabled,
        read_only=True,
        instances=discover_monitor_instances(config=config, symbols=symbols, base_dir=base_dir),
    )


def redact_sensitive_values(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[Any, Any] = {}
        for key, item in value.items():
            if any(keyword in str(key).lower() for keyword in SENSITIVE_KEYWORDS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_sensitive_values(item)
        return redacted
    if isinstance(value, list):
        return [redact_sensitive_values(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive_values(item) for item in value)
    return value
