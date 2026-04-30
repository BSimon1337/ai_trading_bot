from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, render_template
from flask import request as flask_request

from tradingbot.app.runtime_manager import (
    LifecycleEvent,
    ManagedControlAction,
    ManagedRuntime,
    empty_runtime_registry,
    lifecycle_events_for_symbol,
    lifecycle_event_index,
    load_runtime_registry,
    request_restart_runtime_action,
    request_start_runtime_action,
    request_stop_runtime_action,
    reconcile_runtime_registry,
    runtime_state_index,
)
from tradingbot.config.settings import BotConfig, infer_asset_class
from tradingbot.sentiment.scoring import sentiment_availability_state


DEFAULT_REFRESH_SECONDS = 15
DEFAULT_STALE_AFTER_MINUTES = 180
DEFAULT_HISTORY_ISSUE_LIMIT = 5
DEFAULT_ARCHIVE_MARKERS = ("archive", "archived", "history", "historical", "old", "retained")
SENSITIVE_KEYWORDS = ("key", "secret", "token", "password", "credential")
VALUE_SOURCE_FILL = "latest_fill"
VALUE_SOURCE_FILL_DELTA = "latest_fill_delta"
VALUE_SOURCE_SNAPSHOT_DELTA = "snapshot_delta"
VALUE_SOURCE_UNAVAILABLE = "unavailable"
DEFAULT_HEADLINE_PREVIEW_LIMIT = 3
DEFAULT_SENTIMENT_TREND_LIMIT = 5
DEFAULT_CONTROL_ACTIVITY_LIMIT = 25
DEFAULT_RUNTIME_EVENT_LIMIT = 10
DEFAULT_ACTIVE_WARNING_LIMIT = 5


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
    sentiment_availability_state: str = ""
    sentiment_is_fallback: str = ""
    sentiment_observed_at: str = ""
    headline_count: str = ""
    headline_preview: str = ""
    sentiment_window_start: str = ""
    sentiment_window_end: str = ""
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
    timestamp: str = ""
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
class NoteSummary:
    timestamp: str
    symbol: str
    category: str
    message: str
    source: str


@dataclass(frozen=True)
class SentimentSnapshot:
    symbol: str = ""
    label: str = ""
    probability: float | None = None
    source: str = ""
    availability_state: str = "unavailable"
    is_fallback: bool = False
    is_stale: bool = False
    observed_at: str = ""
    decision_mode: str = ""
    message: str = "Sentiment evidence is unavailable."


@dataclass(frozen=True)
class HeadlineEvidencePreview:
    symbol: str = ""
    headline_count: int = 0
    headlines: tuple[str, ...] = ()
    source: str = ""
    window_start: str = ""
    window_end: str = ""
    is_stale: bool = False


@dataclass(frozen=True)
class SentimentTrendEntry:
    timestamp: str = ""
    label: str = ""
    probability: float | None = None
    source: str = ""
    availability_state: str = "unavailable"


@dataclass(frozen=True)
class RuntimeEventEntry:
    event_id: str = ""
    symbol: str = ""
    timestamp_utc: str = ""
    mode_context: str = ""
    runtime_phase: str = ""
    event_source: str = ""
    summary: str = ""
    runtime_session_id: str = ""


@dataclass(frozen=True)
class WarningEvent:
    warning_id: str = ""
    symbol: str = ""
    severity: str = "warning"
    warning_type: str = ""
    origin: str = ""
    timestamp_utc: str = ""
    message: str = ""
    is_active: bool = True


@dataclass(frozen=True)
class OrderLifecycleSummary:
    action_side: str = "n/a"
    lifecycle_state: str = "no_order"
    lifecycle_source: str = "n/a"
    event_time_utc: str = ""
    is_terminal: bool = False
    display_summary: str = "No recent order lifecycle is available."


@dataclass(frozen=True)
class EvidenceFreshnessState:
    freshness_label: str = "unavailable"
    decision_freshness: str = "unavailable"
    fill_freshness: str = "unavailable"
    snapshot_freshness: str = "unavailable"
    runtime_freshness: str = "unavailable"
    explanation: str = "No current evidence is available."


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
    notes: tuple[NoteSummary, ...] = ()
    evidence_scope: str = "active"
    historical_issues: tuple[IssueSummary, ...] = ()
    runtime_state: str = ""
    runtime_status_message: str = ""
    runtime_session_id: str = ""
    runtime_pid: int | None = None
    runtime_started_at_utc: str = ""
    runtime_last_seen_utc: str = ""
    last_lifecycle_event: str = ""
    is_fresh_runtime_session: bool = False
    runtime_mode_context: str = ""
    runtime_lifecycle_events: tuple[LifecycleEvent, ...] = ()


@dataclass(frozen=True)
class MonitorConfiguration:
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS
    tray_enabled: bool = True
    read_only: bool = True
    runtime_registry_path: Path = Path("logs/runtime/runtime_registry.json")
    runtime_event_limit: int = DEFAULT_RUNTIME_EVENT_LIMIT
    active_warning_limit: int = DEFAULT_ACTIVE_WARNING_LIMIT
    recent_control_actions: tuple[ManagedControlAction, ...] = ()
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
        try:
            recovered = pd.read_csv(path, engine="python", on_bad_lines="skip")
        except Exception:
            recovered = pd.DataFrame()
        if not recovered.empty:
            return CsvReadResult(path=path, dataframe=recovered)
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


def _parse_datetime_series(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce", utc=True)
    if parsed.notna().all():
        return parsed
    if parsed.isna().any():
        missing_mask = parsed.isna()
        missing_values = values[missing_mask]
        try:
            reparsed_missing = pd.to_datetime(missing_values, errors="coerce", utc=True, format="mixed")
        except TypeError:
            reparsed_missing = missing_values.apply(lambda value: pd.to_datetime(value, errors="coerce", utc=True))
        parsed.loc[missing_mask] = reparsed_missing
    if parsed.notna().any():
        return parsed
    try:
        parsed = pd.to_datetime(values, errors="coerce", utc=True, format="mixed")
    except TypeError:
        parsed = values.apply(lambda value: pd.to_datetime(value, errors="coerce", utc=True))
    return parsed


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


def to_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


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
    runtime_index: dict[str, ManagedRuntime] | None = None,
    lifecycle_index: dict[str, LifecycleEvent] | None = None,
    lifecycle_events_by_symbol: dict[str, tuple[LifecycleEvent, ...]] | None = None,
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
        runtime = (runtime_index or {}).get(symbol)
        lifecycle_event = (lifecycle_index or {}).get(symbol)
        instances.append(
            DashboardInstance(
                label=symbol,
                symbols=(symbol,),
                asset_classes=(infer_asset_class(symbol),),
                decision_log_path=decision_path,
                fill_log_path=fill_path,
                snapshot_log_path=snapshot_path,
                runtime_state="" if runtime is None else runtime.lifecycle_state,
                runtime_mode_context="" if runtime is None else runtime.mode,
                runtime_status_message=""
                if runtime is None
                else runtime.failure_reason or (lifecycle_event.message if lifecycle_event is not None else runtime.lifecycle_state.replace("_", " ")),
                runtime_session_id="" if runtime is None else runtime.session_id,
                runtime_pid=None if runtime is None else runtime.pid,
                runtime_started_at_utc="" if runtime is None else runtime.started_at_utc,
                runtime_last_seen_utc="" if runtime is None else runtime.last_seen_utc,
                last_lifecycle_event="" if lifecycle_event is None else lifecycle_event.event_type,
                is_fresh_runtime_session=bool(runtime and runtime.lifecycle_state in {"starting", "running", "restarting"}),
                runtime_lifecycle_events=()
                if lifecycle_events_by_symbol is None
                else lifecycle_events_by_symbol.get(symbol, ()),
            )
        )
    return tuple(instances)


def load_runtime_registry_views(
    runtime_registry_path: Path,
) -> tuple[
    dict[str, ManagedRuntime],
    dict[str, LifecycleEvent],
    dict[str, tuple[LifecycleEvent, ...]],
    tuple[ManagedControlAction, ...],
    str,
]:
    try:
        registry = load_runtime_registry(runtime_registry_path)
    except (OSError, ValueError, json.JSONDecodeError):
        registry = empty_runtime_registry()
    runtime_index = runtime_state_index(registry)
    lifecycle_index = lifecycle_event_index(registry)
    lifecycle_events_by_symbol = {
        symbol: lifecycle_events_for_symbol(registry, symbol)
        for symbol in runtime_index
    }
    return (
        runtime_index,
        lifecycle_index,
        lifecycle_events_by_symbol,
        registry.recent_control_actions,
        registry.updated_at_utc,
    )


def load_monitor_configuration(
    config: BotConfig | None = None,
    *,
    symbols: tuple[str, ...] | None = None,
    base_dir: Path = Path("logs"),
) -> MonitorConfiguration:
    refresh_seconds = _safe_int(os.getenv("MONITOR_REFRESH_SECONDS"), DEFAULT_REFRESH_SECONDS)
    dashboard_port = _safe_int(os.getenv("MONITOR_PORT"), 8080)
    stale_after_minutes = _safe_int(os.getenv("MONITOR_STALE_AFTER_MINUTES"), DEFAULT_STALE_AFTER_MINUTES)
    historical_issue_limit = _safe_int(os.getenv("MONITOR_HISTORICAL_ISSUE_LIMIT"), DEFAULT_HISTORY_ISSUE_LIMIT)
    dashboard_host = os.getenv("MONITOR_HOST", "127.0.0.1").strip() or "127.0.0.1"
    tray_enabled = os.getenv("MONITOR_TRAY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
    runtime_event_limit = _safe_int(
        os.getenv(
            "MONITOR_RUNTIME_EVENT_LIMIT",
            getattr(config, "monitor_runtime_event_limit", DEFAULT_RUNTIME_EVENT_LIMIT) if config is not None else DEFAULT_RUNTIME_EVENT_LIMIT,
        ),
        DEFAULT_RUNTIME_EVENT_LIMIT,
    )
    active_warning_limit = _safe_int(
        os.getenv(
            "MONITOR_ACTIVE_WARNING_LIMIT",
            getattr(config, "monitor_active_warning_limit", DEFAULT_ACTIVE_WARNING_LIMIT) if config is not None else DEFAULT_ACTIVE_WARNING_LIMIT,
        ),
        DEFAULT_ACTIVE_WARNING_LIMIT,
    )
    runtime_registry_path = Path(
        os.getenv(
            "RUNTIME_REGISTRY_PATH",
            config.runtime_registry_path if config is not None else "logs/runtime/runtime_registry.json",
        )
    )
    archive_markers = tuple(
        marker.strip().lower()
        for marker in os.getenv("MONITOR_ARCHIVE_MARKERS", ",".join(DEFAULT_ARCHIVE_MARKERS)).split(",")
        if marker.strip()
    ) or DEFAULT_ARCHIVE_MARKERS
    if config is not None:
        reconcile_runtime_registry(config, registry_path=runtime_registry_path)
    runtime_index, lifecycle_index, lifecycle_events_by_symbol, recent_control_actions, _ = load_runtime_registry_views(runtime_registry_path)
    return MonitorConfiguration(
        dashboard_host=dashboard_host,
        dashboard_port=dashboard_port,
        refresh_seconds=refresh_seconds,
        stale_after_minutes=stale_after_minutes,
        historical_issue_limit=historical_issue_limit,
        archive_markers=archive_markers,
        tray_enabled=tray_enabled,
        read_only=True,
        runtime_registry_path=runtime_registry_path,
        runtime_event_limit=runtime_event_limit,
        active_warning_limit=active_warning_limit,
        recent_control_actions=recent_control_actions,
        instances=discover_monitor_instances(
            config=config,
            symbols=symbols,
            base_dir=base_dir,
            runtime_index=runtime_index,
            lifecycle_index=lifecycle_index,
            lifecycle_events_by_symbol=lifecycle_events_by_symbol,
        ),
    )


def _normalized_runtime_mode_context(instance: DashboardInstance) -> str:
    return (instance.runtime_mode_context or "").strip().lower()


def _managed_runtime_mode_context(
    instance: DashboardInstance,
    latest_decision: DecisionSummary | None = None,
    latest_snapshot: SnapshotSummary | None = None,
) -> str:
    runtime_mode = _normalized_runtime_mode_context(instance)
    if runtime_mode in {"live", "paper"}:
        return runtime_mode
    latest_mode = (latest_decision.mode if latest_decision is not None else "") or (
        latest_snapshot.mode if latest_snapshot is not None else ""
    )
    latest_mode = latest_mode.strip().lower()
    if latest_mode in {"active-live", "live"}:
        return "live"
    if latest_mode == "paper":
        return "paper"
    return runtime_mode


def _runtime_truth_instances(
    instances: tuple[DashboardInstance, ...],
    *,
    config: BotConfig,
) -> tuple[tuple[DashboardInstance, ...], tuple[ManagedControlAction, ...]]:
    registry = reconcile_runtime_registry(config)
    runtime_index = runtime_state_index(registry)
    lifecycle_index = lifecycle_event_index(registry)
    lifecycle_events_by_symbol = {
        symbol: lifecycle_events_for_symbol(registry, symbol)
        for symbol in runtime_index
    }
    enriched: list[DashboardInstance] = []
    for instance in instances:
        symbol = instance.symbols[0] if instance.symbols else instance.label
        runtime = runtime_index.get(symbol)
        lifecycle_event = lifecycle_index.get(symbol)
        if runtime is None:
            enriched.append(instance)
            continue
        enriched.append(
            DashboardInstance(
                **{
                    **instance.__dict__,
                    "runtime_state": runtime.lifecycle_state,
                    "runtime_status_message": runtime.failure_reason
                    or (lifecycle_event.message if lifecycle_event is not None else instance.runtime_status_message),
                    "runtime_session_id": runtime.session_id,
                    "runtime_pid": runtime.pid,
                    "runtime_started_at_utc": runtime.started_at_utc,
                    "runtime_last_seen_utc": runtime.last_seen_utc,
                    "last_lifecycle_event": "" if lifecycle_event is None else lifecycle_event.event_type,
                    "is_fresh_runtime_session": runtime.lifecycle_state in {"starting", "running", "restarting"},
                    "runtime_mode_context": runtime.mode or instance.runtime_mode_context,
                    "runtime_lifecycle_events": lifecycle_events_by_symbol.get(symbol, ()),
                }
            )
        )
    return tuple(enriched), registry.recent_control_actions


def _control_availability_for_instance(
    instance: DashboardInstance,
    latest_mode: str = "",
    *,
    config: BotConfig | None = None,
) -> dict[str, Any]:
    runtime_state = (instance.runtime_state or "").strip().lower()
    asset_class = instance.asset_classes[0] if instance.asset_classes else infer_asset_class(instance.label)
    configured_mode = ""
    if config is not None:
        configured_mode = "paper" if config.paper else "live"
    mode_context = (instance.runtime_mode_context or latest_mode or configured_mode or "").strip().lower()
    if runtime_state in {"stopped", "failed", "paused", "unmanaged", ""} and configured_mode:
        mode_context = configured_mode

    if runtime_state in {"starting", "stopping", "restarting"}:
        return {
            "control_asset_class": asset_class,
            "control_mode_context": mode_context,
            "control_runtime_state": runtime_state,
            "can_start": False,
            "can_stop": False,
            "can_restart": False,
            "control_availability_message": f"Runtime is currently {runtime_state}.",
            "requires_live_confirmation": False,
        }
    if runtime_state == "running":
        return {
            "control_asset_class": asset_class,
            "control_mode_context": mode_context,
            "control_runtime_state": runtime_state,
            "can_start": False,
            "can_stop": True,
            "can_restart": True,
            "control_availability_message": "Runtime is currently running.",
            "requires_live_confirmation": False,
        }
    if runtime_state in {"failed", "paused", "stopped"}:
        message = {
            "failed": "Runtime is not currently healthy. Start or restart is available.",
            "paused": "Runtime is paused. Start or restart is available.",
            "stopped": "Runtime is stopped. Start or restart is available.",
        }[runtime_state]
        return {
            "control_asset_class": asset_class,
            "control_mode_context": mode_context,
            "control_runtime_state": runtime_state,
            "can_start": True,
            "can_stop": False,
            "can_restart": True,
            "control_availability_message": message,
            "requires_live_confirmation": False,
        }
    return {
        "control_asset_class": asset_class,
        "control_mode_context": mode_context,
        "control_runtime_state": runtime_state or "unmanaged",
        "can_start": True,
        "can_stop": False,
        "can_restart": False,
        "control_availability_message": "No active managed runtime is registered.",
        "requires_live_confirmation": False,
    }


def _confirmation_state_for_request(
    config: BotConfig,
    *,
    mode_context: str,
    requested_action: str,
    provided_confirmation: str,
) -> tuple[str, str]:
    del config
    normalized_mode = (mode_context or "").strip().lower()
    normalized_action = (requested_action or "").strip().lower()
    del provided_confirmation
    live_actions = {"start", "restart"}
    if normalized_mode != "live" or normalized_action not in live_actions:
        return "not_required", ""
    return "dashboard_session_trusted", ""


def _blocked_control_action(
    *,
    symbol: str,
    requested_action: str,
    mode_context: str,
    asset_class: str,
    confirmation_state: str,
    outcome_message: str,
) -> ManagedControlAction:
    return ManagedControlAction(
        action_id=f"blocked-{requested_action}-{symbol}-{int(datetime.now(timezone.utc).timestamp())}",
        symbol=symbol,
        asset_class=asset_class,
        requested_action=requested_action,
        mode_context=mode_context,
        requested_at_utc=_utc_now_iso(),
        requested_from="dashboard",
        confirmation_state=confirmation_state,
        outcome_state="blocked",
        outcome_message=outcome_message,
        runtime_session_id="",
    )


def _control_action_to_dict(action: ManagedControlAction) -> dict[str, Any]:
    timestamp = pd.to_datetime(action.requested_at_utc, errors="coerce", utc=True)
    requested_at = action.requested_at_utc
    if pd.notna(timestamp):
        requested_at = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    return {
        "action_id": action.action_id,
        "timestamp_utc": action.requested_at_utc,
        "symbol": action.symbol,
        "asset_class": action.asset_class,
        "requested_action": action.requested_action,
        "mode_context": action.mode_context,
        "requested_at_utc": requested_at,
        "requested_from": action.requested_from,
        "confirmation_state": action.confirmation_state,
        "outcome_state": action.outcome_state,
        "outcome_message": action.outcome_message,
        "runtime_session_id": action.runtime_session_id,
    }


def _runtime_event_to_dict(event: RuntimeEventEntry) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "symbol": event.symbol,
        "timestamp_utc": event.timestamp_utc,
        "mode_context": event.mode_context,
        "runtime_phase": event.runtime_phase,
        "event_source": event.event_source,
        "summary": event.summary,
        "runtime_session_id": event.runtime_session_id,
    }


def _warning_event_to_dict(event: WarningEvent) -> dict[str, Any]:
    return {
        "warning_id": event.warning_id,
        "symbol": event.symbol,
        "severity": event.severity,
        "warning_type": event.warning_type,
        "origin": event.origin,
        "timestamp_utc": event.timestamp_utc,
        "message": event.message,
        "is_active": event.is_active,
    }


def _order_lifecycle_to_dict(summary: OrderLifecycleSummary) -> dict[str, Any]:
    return {
        "action_side": summary.action_side,
        "lifecycle_state": summary.lifecycle_state,
        "lifecycle_source": summary.lifecycle_source,
        "event_time_utc": summary.event_time_utc,
        "is_terminal": summary.is_terminal,
        "display_summary": summary.display_summary,
    }


def _freshness_bucket(timestamp_value: str | None, *, stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES) -> str:
    timestamp = _parse_instance_timestamp(timestamp_value)
    if timestamp is None:
        return "unavailable"
    age = _age_minutes(timestamp)
    if age is not None and age > stale_after_minutes:
        return "stale"
    return "current"


def _runtime_events_for_instance(
    instance: DashboardInstance,
    decisions: pd.DataFrame,
    fills: pd.DataFrame,
    latest_decision: DecisionSummary,
    latest_fill: FillSummary,
    *,
    limit: int = DEFAULT_RUNTIME_EVENT_LIMIT,
) -> tuple[RuntimeEventEntry, ...]:
    events: list[RuntimeEventEntry] = []
    def lifecycle_value(event: LifecycleEvent | dict[str, Any], field_name: str) -> str:
        if isinstance(event, dict):
            return _clean_value(event.get(field_name, ""))
        return _clean_value(getattr(event, field_name, ""))

    for event in instance.runtime_lifecycle_events:
        session_id = lifecycle_value(event, "session_id")
        event_type = lifecycle_value(event, "event_type")
        timestamp_utc = lifecycle_value(event, "timestamp_utc")
        symbol = lifecycle_value(event, "symbol") or instance.label
        message = lifecycle_value(event, "message")
        events.append(
            RuntimeEventEntry(
                event_id=f"{instance.label}-runtime-{session_id or event_type or 'event'}-{timestamp_utc}",
                symbol=symbol,
                timestamp_utc=timestamp_utc,
                mode_context=instance.runtime_mode_context or latest_decision.mode or "",
                runtime_phase=event_type or instance.last_lifecycle_event or instance.runtime_state or "runtime",
                event_source="runtime_manager",
                summary=message or instance.runtime_status_message or instance.status.message,
                runtime_session_id=session_id or instance.runtime_session_id,
            )
        )
    if not instance.runtime_lifecycle_events and (instance.last_lifecycle_event or instance.runtime_status_message):
        events.append(
            RuntimeEventEntry(
                event_id=f"{instance.label}-runtime-{instance.runtime_session_id or instance.last_lifecycle_event or 'event'}",
                symbol=instance.label,
                timestamp_utc=instance.runtime_last_seen_utc or instance.runtime_started_at_utc or instance.last_updated_at or "",
                mode_context=instance.runtime_mode_context or latest_decision.mode or "",
                runtime_phase=instance.last_lifecycle_event or instance.runtime_state or "runtime",
                event_source="runtime_manager",
                summary=instance.runtime_status_message or instance.status.message,
                runtime_session_id=instance.runtime_session_id,
            )
        )

    if not fills.empty:
        recent_fill_rows = fills.tail(limit).to_dict(orient="records")
        for row in recent_fill_rows:
            side = str(row.get("side", "")).strip().lower() or "order"
            result = str(row.get("result", "")).strip().lower() or "fill_event"
            quantity = _clean_value(row.get("quantity")) or "?"
            events.append(
                RuntimeEventEntry(
                    event_id=f"{instance.label}-fill-{_clean_value(row.get('order_id')) or _clean_value(row.get('timestamp'))}",
                    symbol=_clean_value(row.get("symbol")) or instance.label,
                    timestamp_utc=_clean_value(row.get("timestamp")),
                    mode_context=_clean_value(row.get("mode")) or instance.runtime_mode_context or "",
                    runtime_phase=result,
                    event_source="fill_log",
                    summary=f"{side} {quantity} {result}".strip(),
                    runtime_session_id=instance.runtime_session_id,
                )
            )
    elif latest_fill.timestamp:
        events.append(
            RuntimeEventEntry(
                event_id=f"{instance.label}-fill-{latest_fill.order_id or latest_fill.timestamp}",
                symbol=instance.label,
                timestamp_utc=latest_fill.timestamp,
                mode_context=latest_fill.mode or instance.runtime_mode_context or "",
                runtime_phase=(latest_fill.result or "fill").strip().lower() or "fill",
                event_source="fill_log",
                summary=f"{(latest_fill.side or 'order').strip().lower()} {latest_fill.result or 'event'}".strip(),
                runtime_session_id=instance.runtime_session_id,
            )
        )

    if not decisions.empty:
        recent_decision_rows = decisions.tail(limit).to_dict(orient="records")
        for row in recent_decision_rows:
            action = str(row.get("action", "")).strip().lower() or "decision"
            result = str(row.get("result", "")).strip().lower() or action
            reason = _clean_value(row.get("reason")) or ""
            events.append(
                RuntimeEventEntry(
                    event_id=f"{instance.label}-decision-{_clean_value(row.get('timestamp'))}-{action}",
                    symbol=_clean_value(row.get("symbol")) or instance.label,
                    timestamp_utc=_clean_value(row.get("timestamp")),
                    mode_context=_clean_value(row.get("mode")) or instance.runtime_mode_context or "",
                    runtime_phase=result,
                    event_source="decision_log",
                    summary=reason or f"{action} {result}".strip(),
                    runtime_session_id=instance.runtime_session_id,
                )
            )
    elif latest_decision.timestamp:
        events.append(
            RuntimeEventEntry(
                event_id=f"{instance.label}-decision-{latest_decision.timestamp}",
                symbol=instance.label,
                timestamp_utc=latest_decision.timestamp,
                mode_context=latest_decision.mode or instance.runtime_mode_context or "",
                runtime_phase=(latest_decision.result or latest_decision.action or "decision").strip().lower() or "decision",
                event_source="decision_log",
                summary=latest_decision.reason or f"{latest_decision.action or 'decision'} {latest_decision.result or ''}".strip(),
                runtime_session_id=instance.runtime_session_id,
            )
        )

    deduped: dict[tuple[str, str, str], RuntimeEventEntry] = {}
    for event in events:
        if not (event.timestamp_utc or event.summary):
            continue
        key = (event.event_source, event.timestamp_utc, event.summary)
        deduped[key] = event
    events = list(deduped.values())
    events.sort(key=lambda event: _parse_instance_timestamp(event.timestamp_utc) or pd.Timestamp.min.tz_localize("UTC"), reverse=True)
    return tuple(events[:limit])


def _warning_events_for_instance(
    instance: DashboardInstance,
    *,
    limit: int = DEFAULT_ACTIVE_WARNING_LIMIT,
) -> tuple[WarningEvent, ...]:
    warnings = []
    runtime_state = (instance.runtime_state or "").strip().lower()
    if runtime_state in {"failed", "blocked", "paused"}:
        warnings.append(
            WarningEvent(
                warning_id=f"{instance.label}-runtime-{runtime_state}",
                symbol=instance.label,
                severity="critical" if runtime_state in {"failed", "blocked"} else "warning",
                warning_type=f"runtime_{runtime_state}",
                origin="runtime_manager",
                timestamp_utc=instance.runtime_last_seen_utc or instance.runtime_started_at_utc or _utc_now_iso(),
                message=instance.runtime_status_message or instance.status.message,
                is_active=True,
            )
        )
    warnings.extend(
        [
        WarningEvent(
            warning_id=f"{instance.label}-{issue.category}-{index}",
            symbol=instance.label,
            severity=issue.severity,
            warning_type=issue.category,
            origin=issue.source,
            timestamp_utc=issue.timestamp,
            message=issue.message,
            is_active=True,
        )
        for index, issue in enumerate(instance.issues, start=1)
        ]
    )
    warnings.sort(
        key=lambda event: _parse_instance_timestamp(event.timestamp_utc) or pd.Timestamp.min.tz_localize("UTC"),
        reverse=True,
    )
    return tuple(warnings[:limit])


def _latest_order_lifecycle_for_instance(
    latest_decision: DecisionSummary,
    latest_fill: FillSummary,
) -> OrderLifecycleSummary:
    fill_state = (latest_fill.result or "").strip().lower()
    if latest_fill.timestamp:
        terminal = fill_state in {"filled", "rejected", "canceled"}
        state = fill_state or "fill_event"
        side = (latest_fill.side or "n/a").strip().lower() or "n/a"
        return OrderLifecycleSummary(
            action_side=side,
            lifecycle_state=state,
            lifecycle_source="fill_log",
            event_time_utc=latest_fill.timestamp,
            is_terminal=terminal,
            display_summary=f"{side} order {state}".strip(),
        )
    decision_state = (latest_decision.result or "").strip().lower()
    decision_action = (latest_decision.action or "").strip().lower()
    if latest_decision.timestamp and decision_action in {"buy", "sell"}:
        state = decision_state or "submitted"
        return OrderLifecycleSummary(
            action_side=decision_action,
            lifecycle_state=state,
            lifecycle_source="decision_log",
            event_time_utc=latest_decision.timestamp,
            is_terminal=state in {"filled", "rejected", "canceled"},
            display_summary=f"{decision_action} order {state}".strip(),
        )
    return OrderLifecycleSummary()


def _freshness_state_for_instance(
    instance: DashboardInstance,
    latest_decision: DecisionSummary,
    latest_fill: FillSummary,
    latest_snapshot: SnapshotSummary,
    *,
    is_provisional: bool,
    held_value_source: str = VALUE_SOURCE_UNAVAILABLE,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> EvidenceFreshnessState:
    if instance.evidence_scope == "historical":
        return EvidenceFreshnessState(
            freshness_label="historical",
            decision_freshness=_freshness_bucket(latest_decision.timestamp, stale_after_minutes=stale_after_minutes),
            fill_freshness=_freshness_bucket(latest_fill.timestamp, stale_after_minutes=stale_after_minutes),
            snapshot_freshness=_freshness_bucket(latest_snapshot.timestamp, stale_after_minutes=stale_after_minutes),
            runtime_freshness=_freshness_bucket(instance.runtime_last_seen_utc, stale_after_minutes=stale_after_minutes),
            explanation="This symbol currently reflects historical evidence outside the active monitor window.",
        )
    if instance.status.state == "no_data":
        return EvidenceFreshnessState(explanation="No current runtime evidence is available for this symbol.")
    if instance.status.state == "stale":
        return EvidenceFreshnessState(
            freshness_label="stale",
            decision_freshness=_freshness_bucket(latest_decision.timestamp, stale_after_minutes=stale_after_minutes),
            fill_freshness=_freshness_bucket(latest_fill.timestamp, stale_after_minutes=stale_after_minutes),
            snapshot_freshness=_freshness_bucket(latest_snapshot.timestamp, stale_after_minutes=stale_after_minutes),
            runtime_freshness=_freshness_bucket(instance.runtime_last_seen_utc, stale_after_minutes=stale_after_minutes),
            explanation=instance.status.message,
        )
    if is_provisional:
        return EvidenceFreshnessState(
            freshness_label="provisional",
            decision_freshness=_freshness_bucket(latest_decision.timestamp, stale_after_minutes=stale_after_minutes),
            fill_freshness=_freshness_bucket(latest_fill.timestamp, stale_after_minutes=stale_after_minutes),
            snapshot_freshness=_freshness_bucket(latest_snapshot.timestamp, stale_after_minutes=stale_after_minutes),
            runtime_freshness=_freshness_bucket(instance.runtime_last_seen_utc, stale_after_minutes=stale_after_minutes),
            explanation="Portfolio values are temporarily derived from fresher fill evidence than the latest snapshot.",
        )
    if held_value_source == VALUE_SOURCE_UNAVAILABLE and to_float(latest_snapshot.position_qty) > 0:
        return EvidenceFreshnessState(
            freshness_label="unavailable",
            decision_freshness=_freshness_bucket(latest_decision.timestamp, stale_after_minutes=stale_after_minutes),
            fill_freshness=_freshness_bucket(latest_fill.timestamp, stale_after_minutes=stale_after_minutes),
            snapshot_freshness=_freshness_bucket(latest_snapshot.timestamp, stale_after_minutes=stale_after_minutes),
            runtime_freshness=_freshness_bucket(instance.runtime_last_seen_utc, stale_after_minutes=stale_after_minutes),
            explanation="Current runtime evidence is available, but symbol-local portfolio value is waiting on a confirmed fill or snapshot update.",
        )
    return EvidenceFreshnessState(
        freshness_label="current",
        decision_freshness=_freshness_bucket(latest_decision.timestamp, stale_after_minutes=stale_after_minutes),
        fill_freshness=_freshness_bucket(latest_fill.timestamp, stale_after_minutes=stale_after_minutes),
        snapshot_freshness=_freshness_bucket(latest_snapshot.timestamp, stale_after_minutes=stale_after_minutes),
        runtime_freshness=_freshness_bucket(instance.runtime_last_seen_utc, stale_after_minutes=stale_after_minutes),
        explanation="Current monitor evidence is aligned with the latest active runtime state.",
    )


def _load_recent_control_actions(
    *,
    config: BotConfig | None = None,
    recent_control_actions: tuple[ManagedControlAction, ...] | None = None,
    runtime_registry_path: Path | None = None,
    limit: int = DEFAULT_CONTROL_ACTIVITY_LIMIT,
) -> tuple[list[dict[str, Any]], str]:
    actions = recent_control_actions
    updated_at_utc = ""
    if actions is None:
        registry_path = Path(
            runtime_registry_path
            or os.getenv(
                "RUNTIME_REGISTRY_PATH",
                config.runtime_registry_path if config is not None else "logs/runtime/runtime_registry.json",
            )
        )
        _, _, _, actions, updated_at_utc = load_runtime_registry_views(registry_path)
    effective_limit = max(1, limit)
    if config is not None:
        effective_limit = max(1, int(config.runtime_recent_control_actions_limit))
    sorted_actions = sorted(actions or (), key=lambda item: item.requested_at_utc, reverse=True)
    if not sorted_actions:
        updated_at_utc = ""
    return ([_control_action_to_dict(action) for action in sorted_actions[:effective_limit]], updated_at_utc)


def _request_value(name: str, default: str = "") -> str:
    payload = flask_request.get_json(silent=True)
    if isinstance(payload, dict):
        value = payload.get(name, default)
        return str(value).strip()
    value = flask_request.form.get(name, default)
    return str(value).strip()


def _control_response(action: ManagedControlAction) -> dict[str, Any]:
    if isinstance(action, dict):
        return action
    return _control_action_to_dict(action)


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


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


def _parse_headline_preview(value: Any, limit: int = DEFAULT_HEADLINE_PREVIEW_LIMIT) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, list):
        headlines = [str(item).strip() for item in value if str(item).strip()]
        return tuple(headlines[:limit])
    text = str(value).strip()
    if not text:
        return ()
    try:
        parsed = json.loads(text)
    except (TypeError, ValueError, json.JSONDecodeError):
        parsed = [text]
    if isinstance(parsed, list):
        headlines = [str(item).strip() for item in parsed if str(item).strip()]
        return tuple(headlines[:limit])
    parsed_text = str(parsed).strip()
    return (parsed_text,) if parsed_text else ()


def _timestamp_is_stale(
    value: str,
    *,
    reference: datetime | None = None,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> bool:
    timestamp = _parse_instance_timestamp(value)
    if timestamp is None:
        return False
    cutoff = _active_evidence_cutoff(reference=reference, active_minutes=stale_after_minutes)
    return timestamp < cutoff


def _infer_sentiment_availability_state(
    source: str,
    label: str,
    headline_count: int,
    explicit_state: str = "",
) -> str:
    if explicit_state:
        return explicit_state
    return sentiment_availability_state(
        source=source,
        label=label,
        headline_count=headline_count,
    )


def _sentiment_state_message(state: str) -> str:
    messages = {
        "news_scored": "FinBERT scored recent external headlines.",
        "local_fixture_scored": "FinBERT scored recent local fixture headlines.",
        "local_fixture_unavailable": "Local fixture news was available, but no usable sentiment evidence was produced.",
        "neutral_fallback": "Using neutral fallback because recent sentiment inputs were unavailable.",
        "no_headlines": "No recent headlines were available for sentiment scoring.",
        "scored": "Recent sentiment evidence was scored successfully.",
        "unavailable": "Sentiment evidence is unavailable.",
        "stale_news_scored": "Latest scored headline sentiment is stale and older than the active monitor window.",
        "stale_local_fixture_scored": "Latest local-fixture sentiment is stale and older than the active monitor window.",
        "stale_local_fixture_unavailable": "Latest local-fixture sentiment evidence is stale and older than the active monitor window.",
        "stale_neutral_fallback": "Fallback sentiment is stale and older than the active monitor window.",
        "stale_no_headlines": "No recent headlines were available, and the latest sentiment context is stale.",
        "stale_scored": "Latest sentiment evidence is stale and older than the active monitor window.",
        "stale_unavailable": "Sentiment evidence is unavailable and stale.",
    }
    return messages.get(state, "Sentiment evidence is available.")


def _sentiment_snapshot(summary: DecisionSummary | None) -> SentimentSnapshot:
    if summary is None:
        return SentimentSnapshot()
    probability = None
    if summary.sentiment_probability:
        probability = to_float(summary.sentiment_probability, default=0.0)
    headline_count = to_int(summary.headline_count, default=0)
    availability_state = _infer_sentiment_availability_state(
        summary.sentiment_source,
        summary.sentiment_label,
        headline_count,
        summary.sentiment_availability_state,
    )
    observed_at = summary.sentiment_observed_at or summary.timestamp
    is_stale = _timestamp_is_stale(observed_at)
    if is_stale and not availability_state.startswith("stale_"):
        availability_state = f"stale_{availability_state}"
    return SentimentSnapshot(
        symbol=summary.symbol,
        label=summary.sentiment_label,
        probability=probability,
        source=summary.sentiment_source,
        availability_state=availability_state,
        is_fallback=to_bool(summary.sentiment_is_fallback, default=summary.sentiment_source == "neutral_fallback"),
        is_stale=is_stale,
        observed_at=observed_at,
        decision_mode=summary.mode,
        message=_sentiment_state_message(availability_state),
    )


def _has_sentiment_evidence(summary: DecisionSummary | None) -> bool:
    if summary is None:
        return False
    evidence_values = (
        summary.sentiment_source,
        summary.sentiment_probability,
        summary.sentiment_label,
        summary.sentiment_availability_state,
        summary.sentiment_is_fallback,
        summary.sentiment_observed_at,
        summary.headline_count,
        summary.headline_preview,
        summary.sentiment_window_start,
        summary.sentiment_window_end,
    )
    return any(str(value or "").strip() for value in evidence_values)


def _latest_sentiment_summary(decisions: pd.DataFrame) -> DecisionSummary | None:
    if decisions.empty:
        return None

    for row in reversed(decisions.to_dict(orient="records")):
        summary = _row_to_summary(row, DecisionSummary)
        if _has_sentiment_evidence(summary):
            return summary
    return None


def _headline_evidence_preview(
    summary: DecisionSummary | None,
    *,
    preview_limit: int = DEFAULT_HEADLINE_PREVIEW_LIMIT,
) -> HeadlineEvidencePreview:
    if summary is None:
        return HeadlineEvidencePreview()
    headlines = _parse_headline_preview(summary.headline_preview, limit=preview_limit)
    headline_count = to_int(summary.headline_count, default=len(headlines))
    return HeadlineEvidencePreview(
        symbol=summary.symbol,
        headline_count=headline_count,
        headlines=headlines,
        source=summary.sentiment_source,
        window_start=summary.sentiment_window_start,
        window_end=summary.sentiment_window_end,
        is_stale=_timestamp_is_stale(summary.sentiment_observed_at or summary.timestamp),
    )


def _sentiment_trend(
    decisions: pd.DataFrame,
    *,
    limit: int = DEFAULT_SENTIMENT_TREND_LIMIT,
) -> tuple[SentimentTrendEntry, ...]:
    if decisions.empty:
        return ()
    trend_entries: list[SentimentTrendEntry] = []
    recent = decisions.tail(limit * 3).to_dict(orient="records")
    for row in reversed(recent):
        summary = _row_to_summary(row, DecisionSummary)
        snapshot = _sentiment_snapshot(summary)
        if not snapshot.label and snapshot.availability_state == "unavailable":
            continue
        trend_entries.append(
            SentimentTrendEntry(
                timestamp=summary.timestamp,
                label=snapshot.label,
                probability=snapshot.probability,
                source=snapshot.source,
                availability_state=snapshot.availability_state,
            )
        )
        if len(trend_entries) >= limit:
            break
    trend_entries.reverse()
    return tuple(trend_entries)


def _sentiment_snapshot_to_dict(snapshot: SentimentSnapshot) -> dict[str, Any]:
    return {
        "symbol": snapshot.symbol,
        "label": snapshot.label,
        "probability": snapshot.probability,
        "source": snapshot.source,
        "availability_state": snapshot.availability_state,
        "is_fallback": snapshot.is_fallback,
        "is_stale": snapshot.is_stale,
        "observed_at": snapshot.observed_at,
        "decision_mode": snapshot.decision_mode,
        "message": snapshot.message,
    }


def _headline_preview_to_dict(preview: HeadlineEvidencePreview) -> dict[str, Any]:
    return {
        "symbol": preview.symbol,
        "headline_count": preview.headline_count,
        "headlines": list(preview.headlines),
        "source": preview.source,
        "window_start": preview.window_start,
        "window_end": preview.window_end,
        "is_stale": preview.is_stale,
    }


def _sentiment_trend_to_dict(entry: SentimentTrendEntry) -> dict[str, Any]:
    return {
        "timestamp": entry.timestamp,
        "label": entry.label,
        "probability": entry.probability,
        "source": entry.source,
        "availability_state": entry.availability_state,
    }


def _row_to_summary(row: dict[str, Any], summary_type: type[DecisionSummary] | type[FillSummary] | type[SnapshotSummary]):
    fields = summary_type.__dataclass_fields__.keys()
    return summary_type(**{field_name: _clean_value(row.get(field_name, "")) for field_name in fields})


def _summary_to_dict(summary: Any | None) -> dict[str, Any]:
    if summary is None:
        return {}
    return {field_name: getattr(summary, field_name) for field_name in summary.__dataclass_fields__}


def _issue_to_dict(issue: IssueSummary) -> dict[str, str]:
    return {
        "timestamp": issue.timestamp,
        "severity": issue.severity,
        "symbol": issue.symbol,
        "category": issue.category,
        "message": issue.message,
        "source": issue.source,
    }


def _note_to_dict(note: NoteSummary) -> dict[str, str]:
    return {
        "timestamp": note.timestamp,
        "symbol": note.symbol,
        "category": note.category,
        "message": note.message,
        "source": note.source,
    }


def _status_to_dict(status: RuntimeStatus) -> dict[str, Any]:
    return {
        "state": status.state,
        "severity": status.severity,
        "message": status.message,
        "age_minutes": status.age_minutes,
    }


def _sort_issues(issues: list[IssueSummary]) -> list[IssueSummary]:
    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    return sorted(
        issues,
        key=lambda issue: (
            severity_rank.get(issue.severity, 99),
            issue.timestamp,
            issue.category,
            issue.symbol,
        ),
        reverse=False,
    )


def _sort_notes(notes: list[NoteSummary]) -> list[NoteSummary]:
    return sorted(
        notes,
        key=lambda note: (note.timestamp, note.category, note.symbol),
        reverse=False,
    )


def _recent_rows(dataframe: pd.DataFrame, limit: int = 15) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    recent = dataframe.tail(limit).copy()
    for column in recent.columns:
        if pd.api.types.is_datetime64_any_dtype(recent[column]):
            recent[column] = recent[column].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return recent.fillna("").to_dict(orient="records")


def _normalize_snapshot_frame(dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe
    normalized = dataframe.copy()
    if "timestamp" not in normalized.columns:
        if "date" in normalized.columns:
            normalized["timestamp"] = _parse_datetime_series(normalized["date"])
        else:
            normalized["timestamp"] = pd.NaT
    else:
        normalized["timestamp"] = _parse_datetime_series(normalized["timestamp"])
    return normalized.sort_values("timestamp")


def _active_evidence_cutoff(
    *,
    reference: datetime | None = None,
    active_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> pd.Timestamp:
    reference_utc = reference or datetime.now(timezone.utc)
    timestamp = pd.Timestamp(reference_utc)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp - pd.Timedelta(minutes=active_minutes)


def _instance_evidence_scope(
    instance: DashboardInstance,
    *,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
) -> str:
    markers = {marker.lower() for marker in archive_markers if marker}
    if not markers:
        return "active"
    for path in (instance.decision_log_path, instance.fill_log_path, instance.snapshot_log_path):
        parts = [part.lower() for part in Path(path).parts]
        if any(marker in part for marker in markers for part in parts):
            return "historical"
    return "active"


def _filter_active_evidence(
    dataframe: pd.DataFrame,
    *,
    column: str = "timestamp",
    reference: datetime | None = None,
    active_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> pd.DataFrame:
    if dataframe.empty or column not in dataframe.columns:
        return dataframe
    cutoff = _active_evidence_cutoff(reference=reference, active_minutes=active_minutes)
    normalized = dataframe.copy()
    normalized[column] = pd.to_datetime(normalized[column], errors="coerce", utc=True)
    return normalized[normalized[column].notna() & (normalized[column] >= cutoff)].sort_values(column)


def _latest_timestamp(*frames: pd.DataFrame) -> pd.Timestamp | None:
    timestamps: list[pd.Timestamp] = []
    for frame in frames:
        if frame.empty or "timestamp" not in frame.columns:
            continue
        timestamp = frame["timestamp"].dropna().iloc[-1] if not frame["timestamp"].dropna().empty else None
        if timestamp is not None and pd.notna(timestamp):
            timestamps.append(timestamp)
    return max(timestamps) if timestamps else None


def _row_issues(frame: pd.DataFrame, source: str) -> list[IssueSummary]:
    issues: list[IssueSummary] = []
    if frame.empty:
        return issues
    for row in frame.tail(20).to_dict(orient="records"):
        reason = str(row.get("reason", ""))
        result = str(row.get("result", ""))
        if result in {"failed", "blocked", "rejected", "canceled"} or reason.startswith("broker_"):
            if result == "blocked":
                category = "blocked"
            elif result in {"rejected", "canceled"} or reason.startswith("broker_"):
                category = "broker_rejection"
            else:
                category = result or "broker_issue"
            issues.append(
                IssueSummary(
                    timestamp=_clean_value(row.get("timestamp")) or _utc_now_iso(),
                    severity="critical" if result in {"failed", "blocked"} else "warning",
                    symbol=_clean_value(row.get("symbol")) or "SYSTEM",
                    category=category,
                    message=reason or result,
                    source=source,
                )
            )
    return issues


def _parse_instance_timestamp(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    timestamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return None
    return timestamp


def _filter_runtime_session_evidence(
    dataframe: pd.DataFrame,
    runtime_started_at_utc: str,
) -> pd.DataFrame:
    if dataframe.empty or "timestamp" not in dataframe.columns or not runtime_started_at_utc:
        return dataframe
    runtime_started_at = _parse_instance_timestamp(runtime_started_at_utc)
    if runtime_started_at is None:
        return dataframe
    return dataframe[dataframe["timestamp"] >= runtime_started_at]


def _select_authoritative_account_instance(
    instances: list[DashboardInstance],
    *,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    reference: datetime | None = None,
) -> DashboardInstance | None:
    if not instances:
        return None
    cutoff = _active_evidence_cutoff(reference=reference, active_minutes=stale_after_minutes)
    candidates: list[tuple[pd.Timestamp, DashboardInstance]] = []
    fallback_candidates: list[tuple[pd.Timestamp, DashboardInstance]] = []
    for instance in instances:
        snapshot = instance.latest_snapshot
        snapshot_ts = _parse_instance_timestamp(snapshot.timestamp if snapshot is not None else None)
        fill = instance.latest_fill
        fill_ts = _parse_instance_timestamp(fill.timestamp if fill is not None else None)
        last_update_ts = _parse_instance_timestamp(instance.last_updated_at)
        evidence_ts = max(
            [timestamp for timestamp in (fill_ts, snapshot_ts, last_update_ts) if timestamp is not None],
            default=None,
        )
        if evidence_ts is not None:
            fallback_candidates.append((evidence_ts, instance))
            if evidence_ts >= cutoff:
                candidates.append((evidence_ts, instance))
    ranked = candidates or fallback_candidates
    if not ranked:
        return instances[0]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _value_evidence(
    snapshot: SnapshotSummary | None,
    fill: FillSummary | None,
    *,
    allow_snapshot_delta: bool = True,
) -> tuple[float, float, str]:
    position_qty = to_float(snapshot.position_qty if snapshot is not None else None)
    fill_qty = to_float(fill.quantity if fill is not None else None)
    fill_notional = to_float(fill.notional_usd if fill is not None else None)
    if fill_qty > 0 and fill_notional > 0:
        unit_value = fill_notional / fill_qty
        return unit_value, position_qty * unit_value, VALUE_SOURCE_FILL

    if not allow_snapshot_delta:
        return 0.0, 0.0, VALUE_SOURCE_UNAVAILABLE

    portfolio_value = to_float(snapshot.portfolio_value if snapshot is not None else None)
    cash = to_float(snapshot.cash if snapshot is not None else None)
    if position_qty > 0 and portfolio_value >= cash:
        held_value = max(portfolio_value - cash, 0.0)
        if held_value > 0:
            return held_value / position_qty, held_value, VALUE_SOURCE_SNAPSHOT_DELTA

    return 0.0, 0.0, VALUE_SOURCE_UNAVAILABLE


def _effective_portfolio_state(
    snapshot: SnapshotSummary | None,
    fill: FillSummary | None,
    *,
    allow_snapshot_delta: bool = True,
) -> dict[str, Any]:
    snapshot_qty = to_float(snapshot.position_qty if snapshot is not None else None)
    snapshot_cash = to_float(snapshot.cash if snapshot is not None else None)
    snapshot_portfolio = to_float(snapshot.portfolio_value if snapshot is not None else None)
    snapshot_timestamp = _parse_instance_timestamp(snapshot.timestamp if snapshot is not None else None)

    fill_timestamp = _parse_instance_timestamp(fill.timestamp if fill is not None else None)
    fill_result = (fill.result if fill is not None else "").strip().lower()
    fill_side = (fill.side if fill is not None else "").strip().lower()
    fill_qty = to_float(fill.quantity if fill is not None else None)
    fill_cash = to_float(fill.cash if fill is not None else None)
    fill_portfolio = to_float(fill.portfolio_value if fill is not None else None)
    fill_notional = to_float(fill.notional_usd if fill is not None else None)

    display_qty = snapshot_qty
    display_cash = snapshot_cash
    display_portfolio = snapshot_portfolio
    value_source = VALUE_SOURCE_UNAVAILABLE

    if fill_timestamp is not None and (snapshot_timestamp is None or fill_timestamp > snapshot_timestamp) and fill_result == "filled":
        if fill_side == "buy" and fill_qty > 0:
            display_qty = snapshot_qty + fill_qty
        elif fill_side == "sell" and fill_qty > 0:
            display_qty = max(snapshot_qty - fill_qty, 0.0)
        if fill_cash > 0:
            display_cash = fill_cash
        if fill_portfolio > 0:
            display_portfolio = fill_portfolio
        if fill_qty > 0 and fill_notional > 0 and display_qty > 0:
            unit_value = fill_notional / fill_qty
            return {
                "position_qty": display_qty,
                "cash": display_cash,
                "portfolio_value": display_portfolio,
                "held_value": display_qty * unit_value,
                "held_value_estimate": display_qty * unit_value,
                "held_value_source": VALUE_SOURCE_FILL_DELTA,
                "latest_fill_price": unit_value,
                "is_provisional": True,
            }

    latest_fill_price, held_value_estimate, held_value_source = _value_evidence(
        snapshot,
        fill,
        allow_snapshot_delta=allow_snapshot_delta,
    )
    held_value = held_value_estimate if held_value_source != VALUE_SOURCE_UNAVAILABLE else None
    return {
        "position_qty": display_qty,
        "cash": display_cash,
        "portfolio_value": display_portfolio,
        "held_value": held_value,
        "held_value_estimate": held_value_estimate,
        "held_value_source": held_value_source,
        "latest_fill_price": latest_fill_price,
        "is_provisional": False,
    }


def _effective_account_state(
    snapshot: SnapshotSummary | None,
    fill: FillSummary | None,
) -> dict[str, Any]:
    snapshot_cash = to_float(snapshot.cash if snapshot is not None else None)
    snapshot_portfolio = to_float(snapshot.portfolio_value if snapshot is not None else None)
    snapshot_timestamp = _parse_instance_timestamp(snapshot.timestamp if snapshot is not None else None)

    fill_timestamp = _parse_instance_timestamp(fill.timestamp if fill is not None else None)
    fill_result = (fill.result if fill is not None else "").strip().lower()
    fill_cash = to_float(fill.cash if fill is not None else None)
    fill_portfolio = to_float(fill.portfolio_value if fill is not None else None)

    is_provisional = False
    account_cash = snapshot_cash
    account_equity = snapshot_portfolio
    source = "snapshot"

    if fill_timestamp is not None and (snapshot_timestamp is None or fill_timestamp > snapshot_timestamp) and fill_result == "filled":
        if fill_cash > 0:
            account_cash = fill_cash
        if fill_portfolio > 0:
            account_equity = fill_portfolio
        is_provisional = True
        source = VALUE_SOURCE_FILL_DELTA

    return {
        "cash": account_cash,
        "account_equity": account_equity,
        "is_provisional": is_provisional,
        "source": source,
    }


def _age_minutes(timestamp: pd.Timestamp | None) -> float | None:
    if timestamp is None or pd.isna(timestamp):
        return None
    return float((datetime.now(timezone.utc) - timestamp.to_pydatetime()).total_seconds() / 60.0)


def _classify_status(
    instance: DashboardInstance,
    latest_decision: DecisionSummary | None,
    latest_snapshot: SnapshotSummary | None,
    issues: list[IssueSummary],
    age_minutes: float | None,
    stale_after_minutes: int,
) -> RuntimeStatus:
    runtime_state = instance.runtime_state
    runtime_message = instance.runtime_status_message or "Runtime state updated by runtime manager."
    runtime_mode = _managed_runtime_mode_context(instance, latest_decision, latest_snapshot)
    if runtime_state == "failed":
        return RuntimeStatus("failed", "critical", runtime_message, age_minutes)
    if runtime_state == "blocked":
        return RuntimeStatus("blocked", "critical", runtime_message, age_minutes)
    if runtime_state == "paused":
        return RuntimeStatus("paused", "warning", runtime_message, age_minutes)
    if runtime_state == "stopped":
        return RuntimeStatus("stopped", "info", runtime_message, age_minutes)
    if runtime_state == "stopping":
        return RuntimeStatus("stopped", "warning", runtime_message, age_minutes)
    if runtime_state in {"starting", "restarting"}:
        if runtime_mode == "live":
            return RuntimeStatus("live", "info", runtime_message or "Managed live runtime is starting.", age_minutes)
        if runtime_mode == "paper":
            return RuntimeStatus("paper", "info", runtime_message or "Managed paper runtime is starting.", age_minutes)
        return RuntimeStatus("running", "info", runtime_message, age_minutes)

    if latest_decision is None:
        if runtime_state == "running":
            if runtime_mode == "live":
                return RuntimeStatus("live", "ok", runtime_message or "Managed live runtime is running.", age_minutes)
            if runtime_mode == "paper":
                return RuntimeStatus("paper", "info", runtime_message or "Managed paper runtime is running.", age_minutes)
            return RuntimeStatus("running", "info", runtime_message, age_minutes)
        return RuntimeStatus("no_data", "warning", "No runtime evidence found.", age_minutes)
    live_like = latest_decision.mode in {"active-live", "live"} or runtime_mode == "live"
    paper_like = latest_decision.mode == "paper" or runtime_mode == "paper"
    if runtime_state == "running":
        if live_like:
            return RuntimeStatus("live", "ok", runtime_message or "Managed live runtime is running.", age_minutes)
        if paper_like:
            return RuntimeStatus("paper", "info", runtime_message or "Managed paper runtime is running.", age_minutes)
        return RuntimeStatus("running", "ok", runtime_message, age_minutes)
    if latest_decision.mode == "blocked-live" or latest_decision.result == "blocked":
        return RuntimeStatus("blocked", "critical", latest_decision.reason or "Live run was blocked.", age_minutes)
    if latest_decision.result == "failed":
        return RuntimeStatus("failed", "critical", latest_decision.reason or "Runtime failed.", age_minutes)
    critical_issues = [issue for issue in issues if issue.severity == "critical"]
    if critical_issues:
        top_issue = critical_issues[0]
        if top_issue.category == "blocked":
            return RuntimeStatus("blocked", "critical", top_issue.message or "Live run was blocked.", age_minutes)
        return RuntimeStatus("failed", "critical", top_issue.message or "Recent critical issue found.", age_minutes)
    if age_minutes is not None and age_minutes > stale_after_minutes:
        return RuntimeStatus("stale", "warning", f"Latest evidence is {age_minutes:.1f} minutes old.", age_minutes)
    if any(issue.category in {"malformed_csv", "broker_rejection", "rejected", "canceled"} for issue in issues):
        top_issue = next(
            issue for issue in issues if issue.category in {"malformed_csv", "broker_rejection", "rejected", "canceled"}
        )
        if live_like:
            return RuntimeStatus("live", "warning", top_issue.message or "Recent runtime warning found.", age_minutes)
        if paper_like:
            return RuntimeStatus("paper", "warning", top_issue.message or "Recent runtime warning found.", age_minutes)
        return RuntimeStatus("running", "warning", top_issue.message or "Recent runtime warning found.", age_minutes)
    if live_like:
        return RuntimeStatus("live", "ok", "Live runtime evidence is updating.", age_minutes)
    if paper_like:
        return RuntimeStatus("paper", "info", "Paper runtime evidence is updating.", age_minutes)
    return RuntimeStatus("running", "ok", "Runtime evidence is updating.", age_minutes)


def _collect_recent_activity(instances: list[DashboardInstance], limit: int = 30) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for instance in instances:
        decisions = normalize_timestamps(safe_read_csv(instance.decision_log_path, source="decisions").dataframe)
        if decisions.empty:
            continue
        recent = decisions.tail(limit).copy()
        for _, row in recent.iterrows():
            row_dict = {column: _clean_value(row.get(column, "")) for column in recent.columns}
            row_dict["instance_label"] = instance.label
            rows.append(row_dict)
    def sort_key(item: dict[str, Any]) -> pd.Timestamp:
        value = pd.to_datetime(item.get("timestamp"), errors="coerce", utc=True)
        if pd.isna(value):
            return pd.Timestamp.min.tz_localize("UTC")
        return value
    rows.sort(key=sort_key, reverse=True)
    normalized_rows: list[dict[str, Any]] = []
    for row in rows[:limit]:
        timestamp = pd.to_datetime(row.get("timestamp"), errors="coerce", utc=True)
        if pd.notna(timestamp):
            row["timestamp"] = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        normalized_rows.append(row)
    return normalized_rows


def _issues_from_evidence(
    read_results: tuple[CsvReadResult, ...],
    decisions: pd.DataFrame,
    fills: pd.DataFrame,
    snapshot: pd.DataFrame,
    age_minutes: float | None,
    stale_after_minutes: int,
    *,
    evidence_scope: str = "active",
    runtime_state: str = "",
) -> list[IssueSummary]:
    issues: list[IssueSummary] = []
    if evidence_scope != "historical":
        issues.extend(result.issue for result in read_results if result.issue is not None)
    if (
        evidence_scope != "historical"
        and runtime_state not in {"stopped", "stopping"}
        and age_minutes is not None
        and age_minutes > stale_after_minutes
    ):
        issues.append(
            IssueSummary(
                timestamp=_utc_now_iso(),
                severity="warning",
                symbol="SYSTEM",
                category="stale_data",
                message=f"Latest runtime evidence is {age_minutes:.1f} minutes old.",
                source="monitor",
            )
        )
    for frame, source in ((decisions, "decisions"), (fills, "fills")):
        issues.extend(_row_issues(frame, source))
    return [issue for issue in _sort_issues([issue for issue in issues if issue is not None])]


def _historical_issues_from_evidence(
    read_results: tuple[CsvReadResult, ...],
    decisions: pd.DataFrame,
    fills: pd.DataFrame,
    active_decisions: pd.DataFrame,
    active_fills: pd.DataFrame,
    *,
    evidence_scope: str,
    historical_issue_limit: int,
) -> list[IssueSummary]:
    historical_issues: list[IssueSummary] = []
    if evidence_scope == "historical":
        historical_issues.extend(result.issue for result in read_results if result.issue is not None)
        historical_decisions = decisions
        historical_fills = fills
    else:
        historical_decisions = decisions
        historical_fills = fills
        if not active_decisions.empty and "timestamp" in active_decisions.columns:
            cutoff = active_decisions["timestamp"].min()
            historical_decisions = decisions[decisions["timestamp"] < cutoff]
        if not active_fills.empty and "timestamp" in active_fills.columns:
            cutoff = active_fills["timestamp"].min()
            historical_fills = fills[fills["timestamp"] < cutoff]

    historical_issues.extend(_row_issues(historical_decisions, "decisions"))
    historical_issues.extend(_row_issues(historical_fills, "fills"))
    sorted_issues = _sort_issues([issue for issue in historical_issues if issue is not None])
    return sorted_issues[:historical_issue_limit]


def _notes_from_evidence(
    decisions: pd.DataFrame,
    fills: pd.DataFrame,
    snapshot: pd.DataFrame,
    *,
    runtime_state: str = "",
    age_minutes: float | None = None,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> list[NoteSummary]:
    del decisions, fills
    notes: list[NoteSummary] = []
    if runtime_state in {"stopped", "failed"} and age_minutes is not None and age_minutes > stale_after_minutes:
        notes.append(
            NoteSummary(
                timestamp=_utc_now_iso(),
                symbol="SYSTEM",
                category="historical_runtime_evidence",
                message="Historical evidence below is from the most recent managed runtime session.",
                source="monitor",
            )
        )
    if not snapshot.empty:
        recent_snapshot = snapshot.tail(5).to_dict(orient="records")
        for row in recent_snapshot:
            day_pnl = to_float(row.get("day_pnl"), 0.0)
            if day_pnl < 0:
                notes.append(
                    NoteSummary(
                        timestamp=_clean_value(row.get("timestamp")) or _utc_now_iso(),
                        symbol=_clean_value(row.get("symbol")) or "SYSTEM",
                        category="negative_pnl",
                        message=f"Latest day PnL is negative: {day_pnl:.2f}",
                        source="snapshot",
                    )
                )
                break
    return _sort_notes(notes)


def summarize_instance(
    instance: DashboardInstance,
    *,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
) -> DashboardInstance:
    evidence_scope = _instance_evidence_scope(instance, archive_markers=archive_markers)
    decision_result = safe_read_csv(instance.decision_log_path, source="decisions")
    fill_result = safe_read_csv(instance.fill_log_path, source="fills")
    snapshot_result = safe_read_csv(instance.snapshot_log_path, source="snapshot")
    decisions = normalize_timestamps(decision_result.dataframe)
    fills = normalize_timestamps(fill_result.dataframe)
    snapshot = _normalize_snapshot_frame(snapshot_result.dataframe)
    if instance.is_fresh_runtime_session and instance.runtime_started_at_utc:
        decisions = _filter_runtime_session_evidence(decisions, instance.runtime_started_at_utc)
        fills = _filter_runtime_session_evidence(fills, instance.runtime_started_at_utc)
        snapshot = _filter_runtime_session_evidence(snapshot, instance.runtime_started_at_utc)
    active_decisions = _filter_active_evidence(decisions, active_minutes=stale_after_minutes)
    active_fills = _filter_active_evidence(fills, active_minutes=stale_after_minutes)
    active_snapshot = _filter_active_evidence(snapshot, active_minutes=stale_after_minutes)

    latest_decision = (
        _row_to_summary(
            (active_decisions.iloc[-1] if not active_decisions.empty else decisions.iloc[-1]).to_dict(),
            DecisionSummary,
        )
        if not decisions.empty
        else None
    )
    latest_fill = (
        _row_to_summary(
            (active_fills.iloc[-1] if not active_fills.empty else fills.iloc[-1]).to_dict(),
            FillSummary,
        )
        if not fills.empty
        else None
    )
    latest_snapshot = (
        _row_to_summary(
            (active_snapshot.iloc[-1] if not active_snapshot.empty else snapshot.iloc[-1]).to_dict(),
            SnapshotSummary,
        )
        if not snapshot.empty
        else None
    )
    last_timestamp = _latest_timestamp(decisions, fills)
    age = _age_minutes(last_timestamp)
    issues = _issues_from_evidence(
        (decision_result, fill_result, snapshot_result),
        active_decisions,
        active_fills,
        active_snapshot,
        age,
        stale_after_minutes,
        evidence_scope=evidence_scope,
        runtime_state=instance.runtime_state,
    )
    historical_issues = _historical_issues_from_evidence(
        (decision_result, fill_result, snapshot_result),
        decisions,
        fills,
        active_decisions,
        active_fills,
        evidence_scope=evidence_scope,
        historical_issue_limit=historical_issue_limit,
    )
    notes = _notes_from_evidence(
        active_decisions,
        active_fills,
        active_snapshot,
        runtime_state=instance.runtime_state,
        age_minutes=age,
        stale_after_minutes=stale_after_minutes,
    )
    status = _classify_status(instance, latest_decision, latest_snapshot, issues, age, stale_after_minutes)
    return DashboardInstance(
        label=instance.label,
        symbols=instance.symbols,
        asset_classes=instance.asset_classes,
        decision_log_path=instance.decision_log_path,
        fill_log_path=instance.fill_log_path,
        snapshot_log_path=instance.snapshot_log_path,
        status=status,
        last_updated_at=None if last_timestamp is None else last_timestamp.isoformat(),
        latest_decision=latest_decision,
        latest_fill=latest_fill,
        latest_snapshot=latest_snapshot,
        issues=tuple(issues),
        notes=tuple(notes),
        evidence_scope=evidence_scope,
        historical_issues=tuple(historical_issues),
        runtime_state=instance.runtime_state,
        runtime_status_message=instance.runtime_status_message,
        runtime_session_id=instance.runtime_session_id,
        runtime_pid=instance.runtime_pid,
        runtime_started_at_utc=instance.runtime_started_at_utc,
        runtime_last_seen_utc=instance.runtime_last_seen_utc,
        last_lifecycle_event=instance.last_lifecycle_event,
        is_fresh_runtime_session=instance.is_fresh_runtime_session,
        runtime_mode_context=instance.runtime_mode_context,
        runtime_lifecycle_events=instance.runtime_lifecycle_events,
    )


def _instance_payload(
    instance: DashboardInstance,
    *,
    config: BotConfig | None = None,
    active_instance_count: int = 1,
) -> dict[str, Any]:
    latest_decision = instance.latest_decision or DecisionSummary()
    latest_fill = instance.latest_fill or FillSummary()
    latest_snapshot = instance.latest_snapshot or SnapshotSummary()
    effective_mode = _managed_runtime_mode_context(instance, latest_decision, latest_snapshot) or "unknown"
    decisions = normalize_timestamps(safe_read_csv(instance.decision_log_path, source="decisions").dataframe)
    fills = normalize_timestamps(safe_read_csv(instance.fill_log_path, source="fills").dataframe)
    snapshot = _normalize_snapshot_frame(safe_read_csv(instance.snapshot_log_path, source="snapshot").dataframe)
    now_utc_date = datetime.now(timezone.utc).date()
    decisions_today = 0
    fills_today = 0
    if not decisions.empty and "timestamp" in decisions.columns:
        decisions_today = int((decisions["timestamp"].dt.date == now_utc_date).sum())
    if not fills.empty and "timestamp" in fills.columns:
        fills_today = int((fills["timestamp"].dt.date == now_utc_date).sum())
    equity_points: list[float] = []
    pnl_points: list[float] = []
    if not snapshot.empty:
        snapshot = snapshot.copy()
        snapshot["portfolio_value"] = pd.to_numeric(snapshot.get("portfolio_value"), errors="coerce")
        snapshot["day_pnl"] = pd.to_numeric(snapshot.get("day_pnl"), errors="coerce")
        snapshot = snapshot.fillna(0)
        equity_points = snapshot["portfolio_value"].astype(float).tail(30).tolist()
        pnl_points = snapshot["day_pnl"].astype(float).tail(30).tolist()
    actions_7d = {"buy": 0, "sell": 0, "hold": 0, "flat": 0}
    if not decisions.empty and "timestamp" in decisions.columns and "action" in decisions.columns:
        recent = decisions[decisions["timestamp"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)]
        counts = recent["action"].astype(str).value_counts().to_dict()
        for action in actions_7d:
            actions_7d[action] = int(counts.get(action, 0))
    recent_decisions = _recent_rows(decisions)
    recent_fills = _recent_rows(fills)
    effective_portfolio = _effective_portfolio_state(
        latest_snapshot,
        latest_fill,
        allow_snapshot_delta=active_instance_count <= 1,
    )
    sentiment_summary = _latest_sentiment_summary(decisions) or latest_decision
    current_sentiment = _sentiment_snapshot(sentiment_summary)
    headline_preview = _headline_evidence_preview(sentiment_summary)
    sentiment_trend = _sentiment_trend(decisions)
    broker_rejection_count = 0
    for frame in (decisions, fills):
        if frame.empty:
            continue
        for row in frame.to_dict(orient="records"):
            reason = str(row.get("reason", ""))
            result = str(row.get("result", ""))
            if result in {"rejected", "canceled"} or reason.startswith("broker_"):
                broker_rejection_count += 1
    control_availability = _control_availability_for_instance(
        instance,
        effective_mode,
        config=config,
    )
    runtime_event_limit = getattr(config, "monitor_runtime_event_limit", DEFAULT_RUNTIME_EVENT_LIMIT) if config is not None else DEFAULT_RUNTIME_EVENT_LIMIT
    active_warning_limit = getattr(config, "monitor_active_warning_limit", DEFAULT_ACTIVE_WARNING_LIMIT) if config is not None else DEFAULT_ACTIVE_WARNING_LIMIT
    recent_runtime_events = _runtime_events_for_instance(
        instance,
        decisions,
        fills,
        latest_decision,
        latest_fill,
        limit=runtime_event_limit,
    )
    active_warnings = _warning_events_for_instance(instance, limit=active_warning_limit)
    latest_order_lifecycle = _latest_order_lifecycle_for_instance(latest_decision, latest_fill)
    freshness_state = _freshness_state_for_instance(
        instance,
        latest_decision,
        latest_fill,
        latest_snapshot,
        is_provisional=effective_portfolio["is_provisional"],
        held_value_source=effective_portfolio["held_value_source"],
    )
    return {
        "label": instance.label,
        "status": _status_to_dict(instance.status),
        "status_state": instance.status.state,
        "status_severity": instance.status.severity,
        "status_reason": instance.status.message,
        "symbols": list(instance.symbols),
        "asset_classes": list(instance.asset_classes),
        "latest_action": latest_decision.action or "n/a",
        "latest_reason": latest_decision.reason or instance.status.message,
        "latest_mode": effective_mode,
        "latest_asset_class": latest_decision.asset_class or (instance.asset_classes[0] if instance.asset_classes else "unknown"),
        "latest_source": latest_decision.action_source or "n/a",
        "latest_update_utc": instance.last_updated_at,
        "runtime_state": instance.runtime_state,
        "runtime_mode_context": effective_mode,
        "runtime_status_message": instance.runtime_status_message,
        "runtime_session_id": instance.runtime_session_id,
        "runtime_pid": instance.runtime_pid,
        "runtime_started_at_utc": instance.runtime_started_at_utc,
        "runtime_last_seen_utc": instance.runtime_last_seen_utc,
        "last_lifecycle_event": instance.last_lifecycle_event,
        "is_fresh_runtime_session": instance.is_fresh_runtime_session,
        "control_asset_class": control_availability["control_asset_class"],
        "control_mode_context": control_availability["control_mode_context"],
        "control_runtime_state": control_availability["control_runtime_state"],
        "can_start": control_availability["can_start"],
        "can_stop": control_availability["can_stop"],
        "can_restart": control_availability["can_restart"],
        "control_availability_message": control_availability["control_availability_message"],
        "requires_live_confirmation": control_availability["requires_live_confirmation"],
        "control_confirmation_hint": (
            "Live controls use this trusted local dashboard session."
            if control_availability["control_mode_context"] == "live"
            else "Paper controls are available from the dashboard."
        ),
        "last_decision_utc": latest_decision.timestamp or "",
        "last_fill_utc": latest_fill.timestamp or "",
        "heartbeat_age_minutes": instance.status.age_minutes,
        "broker_rejection_count": broker_rejection_count,
        "sentiment_label": current_sentiment.label,
        "sentiment_probability": current_sentiment.probability,
        "sentiment_source": current_sentiment.source,
        "sentiment_availability_state": current_sentiment.availability_state,
        "sentiment_is_fallback": current_sentiment.is_fallback,
        "sentiment_is_stale": current_sentiment.is_stale,
        "sentiment_last_updated_utc": current_sentiment.observed_at,
        "sentiment_state_message": current_sentiment.message,
        "headline_count": headline_preview.headline_count,
        "headline_preview": list(headline_preview.headlines),
        "sentiment_trend": [_sentiment_trend_to_dict(entry) for entry in sentiment_trend],
        "sentiment_headline_source_window": {
            "source": headline_preview.source,
            "window_start": headline_preview.window_start,
            "window_end": headline_preview.window_end,
            "is_stale": headline_preview.is_stale,
        },
        "sentiment_snapshot": _sentiment_snapshot_to_dict(current_sentiment),
        "headline_preview_detail": _headline_preview_to_dict(headline_preview),
        "evidence_scope": instance.evidence_scope,
        "historical_issue_count": len(instance.historical_issues),
        "historical_issues": [_issue_to_dict(issue) for issue in instance.historical_issues],
        "account_equity": effective_portfolio["portfolio_value"],
        "portfolio_value": effective_portfolio["portfolio_value"],
        "cash": effective_portfolio["cash"],
        "day_pnl": to_float(latest_snapshot.day_pnl),
        "position_qty": effective_portfolio["position_qty"],
        "held_value": effective_portfolio["held_value"],
        "held_value_estimate": effective_portfolio["held_value_estimate"],
        "held_value_source": effective_portfolio["held_value_source"],
        "latest_fill_price": effective_portfolio["latest_fill_price"],
        "portfolio_is_provisional": effective_portfolio["is_provisional"],
        "recent_runtime_events": [_runtime_event_to_dict(event) for event in recent_runtime_events],
        "active_warnings": [_warning_event_to_dict(event) for event in active_warnings],
        "latest_order_lifecycle": _order_lifecycle_to_dict(latest_order_lifecycle),
        "freshness_state": freshness_state.freshness_label,
        "freshness_explanation": freshness_state.explanation,
        "decisions_today": decisions_today,
        "fills_today": fills_today,
        "equity_points": equity_points,
        "pnl_points": pnl_points,
        "actions_7d": actions_7d,
        "recent_decisions": recent_decisions,
        "recent_fills": recent_fills,
        "recent_decisions_columns": list(decisions.columns) if not decisions.empty else list(DecisionSummary.__dataclass_fields__.keys()),
        "recent_decisions_rows": recent_decisions,
        "recent_fills_columns": list(fills.columns) if not fills.empty else list(FillSummary.__dataclass_fields__.keys()),
        "recent_fills_rows": recent_fills,
        "issues": [_issue_to_dict(issue) for issue in instance.issues],
        "notes": [_note_to_dict(note) for note in instance.notes],
    }


def _aggregate_state(instances: list[DashboardInstance]) -> str:
    active_instances = [instance for instance in instances if instance.evidence_scope != "historical"]
    considered = active_instances or instances
    states = {instance.status.state for instance in considered}
    if not considered:
        return "no_data"
    for state in ("failed", "blocked", "paused", "stale", "no_data"):
        if state in states:
            return state
    if "live" in states:
        return "live"
    if "paper" in states:
        return "paper"
    if "running" in states:
        return "running"
    if "stopped" in states:
        return "stopped"
    return "running"


def _build_account_overview(instances: list[DashboardInstance]) -> dict[str, Any]:
    active_instances = [instance for instance in instances if instance.evidence_scope != "historical"]
    if not active_instances:
        return {
            "account_equity": 0.0,
            "cash": 0.0,
            "day_pnl": 0.0,
            "active_instances": 0,
            "instances_count": 0,
            "fills_today": 0,
            "instances_with_fills": 0,
            "source_instance": "",
            "latest_update_utc": "",
            "is_stale": True,
        }

    freshest = _select_authoritative_account_instance(active_instances)
    if freshest is None:
        return {
            "account_equity": 0.0,
            "cash": 0.0,
            "day_pnl": 0.0,
            "active_instances": len(active_instances),
            "instances_count": len(active_instances),
            "fills_today": 0,
            "instances_with_fills": 0,
            "source_instance": "",
            "latest_update_utc": "",
            "is_stale": True,
        }
    snapshot = freshest.latest_snapshot or SnapshotSummary()
    effective_account = _effective_account_state(snapshot, freshest.latest_fill)
    latest_update = snapshot.timestamp or freshest.last_updated_at or ""
    latest_update_ts = _parse_instance_timestamp(latest_update)
    is_stale = True if latest_update_ts is None else (_age_minutes(latest_update_ts) or 0.0) > DEFAULT_STALE_AFTER_MINUTES
    instances_with_fills = sum(1 for instance in active_instances if instance.latest_fill is not None)
    return {
        "account_equity": effective_account["account_equity"],
        "cash": effective_account["cash"],
        "day_pnl": to_float(snapshot.day_pnl),
        "active_instances": len(active_instances),
        "instances_count": len(active_instances),
        "fills_today": instances_with_fills,
        "instances_with_fills": instances_with_fills,
        "source_instance": freshest.label,
        "latest_update_utc": latest_update,
        "is_stale": is_stale,
        "is_provisional": effective_account["is_provisional"],
        "source": effective_account["source"],
    }


def _build_historical_context(
    instances: list[DashboardInstance],
    *,
    stale_after_minutes: int,
    historical_issue_limit: int,
) -> dict[str, Any]:
    historical_instances = [instance for instance in instances if instance.evidence_scope == "historical"]
    historical_issues = [issue for instance in instances for issue in instance.historical_issues]
    return {
        "active_window_minutes": stale_after_minutes,
        "historical_issue_limit": historical_issue_limit,
        "historical_instance_count": len(historical_instances),
        "historical_issue_count": len(historical_issues),
        "historical_issues": [_issue_to_dict(issue) for issue in _sort_issues(historical_issues)[:historical_issue_limit]],
    }


def dashboard_status(
    instances: tuple[DashboardInstance, ...] | None = None,
    *,
    config: BotConfig | None = None,
    recent_control_actions: tuple[ManagedControlAction, ...] | None = None,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
) -> dict[str, Any]:
    configured = instances if instances is not None else load_monitor_configuration(config=config).instances
    effective_recent_control_actions = recent_control_actions
    if config is not None and instances is not None:
        configured, effective_recent_control_actions = _runtime_truth_instances(configured, config=config)
    summarized = [
        summarize_instance(
            instance,
            stale_after_minutes=stale_after_minutes,
            historical_issue_limit=historical_issue_limit,
            archive_markers=archive_markers,
        )
        for instance in configured
    ]
    active_instances = [instance for instance in summarized if instance.evidence_scope != "historical"]
    display_instances = active_instances or summarized
    active_instance_count = len(active_instances)
    issues = [issue for instance in display_instances for issue in instance.issues]
    notes = [note for instance in display_instances for note in instance.notes]
    recent_activity = _collect_recent_activity(display_instances)
    recent_control_rows, latest_control_updated_at_utc = _load_recent_control_actions(
        config=config,
        recent_control_actions=effective_recent_control_actions,
    )
    payload = {
        "status_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "aggregate_state": _aggregate_state(summarized),
        "account_overview": _build_account_overview(summarized),
        "historical_context": _build_historical_context(
            summarized,
            stale_after_minutes=stale_after_minutes,
            historical_issue_limit=historical_issue_limit,
        ),
        "instances": [
            _instance_payload(
                instance,
                config=config,
                active_instance_count=active_instance_count or len(display_instances),
            )
            for instance in display_instances
        ],
        "recent_control_actions": recent_control_rows,
        "latest_control_updated_at_utc": latest_control_updated_at_utc,
        "recent_control_activity_count": len(recent_control_rows),
        "issues": [_issue_to_dict(issue) for issue in issues],
        "notes": [_note_to_dict(note) for note in _sort_notes(notes)],
        "recent_activity_columns": ["timestamp", "instance_label", "mode", "symbol", "action", "action_source", "quantity", "reason", "result"],
        "recent_activity_rows": recent_activity,
    }
    return redact_sensitive_values(payload)


def create_app(
    *,
    instances: tuple[DashboardInstance, ...] | None = None,
    config: BotConfig | None = None,
    recent_control_actions: tuple[ManagedControlAction, ...] | None = None,
    start_action_runner: Any = request_start_runtime_action,
    stop_action_runner: Any = request_stop_runtime_action,
    restart_action_runner: Any = request_restart_runtime_action,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
    refresh_runtime_state: bool = False,
) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[2] / "templates"))

    def status_payload() -> dict[str, Any]:
        current_instances = instances
        current_recent_control_actions = recent_control_actions
        if refresh_runtime_state and config is not None:
            try:
                current_monitor_configuration = load_monitor_configuration(config=config)
            except Exception:
                current_monitor_configuration = None
            if current_monitor_configuration is not None:
                current_instances = current_monitor_configuration.instances
                current_recent_control_actions = current_monitor_configuration.recent_control_actions
        return dashboard_status(
            current_instances,
            config=config,
            recent_control_actions=current_recent_control_actions,
            stale_after_minutes=stale_after_minutes,
            historical_issue_limit=historical_issue_limit,
            archive_markers=archive_markers,
        )

    @app.route("/")
    def dashboard():
        payload = status_payload()
        return render_template("monitor.html", **payload, refresh_seconds=refresh_seconds)

    @app.route("/health")
    def health():
        payload = status_payload()
        return jsonify(
            {
                "ok": True,
                "time_utc": datetime.now(timezone.utc).isoformat(),
                "monitor_state": payload["aggregate_state"],
                "instances_count": len(payload["instances"]),
            }
        )

    @app.route("/api/status")
    def api_status():
        return jsonify(status_payload())

    @app.route("/control/start", methods=["POST"])
    def control_start():
        if config is None:
            return jsonify({"outcome_state": "blocked", "outcome_message": "Runtime control configuration is unavailable."}), 503
        symbol = _request_value("symbol")
        if not symbol:
            return jsonify({"outcome_state": "blocked", "outcome_message": "A symbol is required."}), 400
        mode_context = _request_value("mode_context", "paper" if config.paper else "live") or ("paper" if config.paper else "live")
        confirmation_value = _request_value("live_confirmation")
        confirmation_state, confirmation_error = _confirmation_state_for_request(
            config,
            mode_context=mode_context,
            requested_action="start",
            provided_confirmation=confirmation_value,
        )
        if confirmation_error:
            return jsonify(
                _control_response(
                    _blocked_control_action(
                        symbol=symbol,
                        requested_action="start",
                        mode_context=mode_context,
                        asset_class=infer_asset_class(symbol),
                        confirmation_state=confirmation_state,
                        outcome_message=confirmation_error,
                    )
                )
            )
        action = start_action_runner(
            config,
            symbol,
            mode="paper" if mode_context == "paper" else "live",
            requested_from="dashboard",
            confirmation_state=confirmation_state,
        )
        return jsonify(_control_response(action))

    @app.route("/control/stop", methods=["POST"])
    def control_stop():
        if config is None:
            return jsonify({"outcome_state": "blocked", "outcome_message": "Runtime control configuration is unavailable."}), 503
        symbol = _request_value("symbol")
        if not symbol:
            return jsonify({"outcome_state": "blocked", "outcome_message": "A symbol is required."}), 400
        action = stop_action_runner(
            config,
            symbol,
            requested_from="dashboard",
        )
        return jsonify(_control_response(action))

    @app.route("/control/restart", methods=["POST"])
    def control_restart():
        if config is None:
            return jsonify({"outcome_state": "blocked", "outcome_message": "Runtime control configuration is unavailable."}), 503
        symbol = _request_value("symbol")
        if not symbol:
            return jsonify({"outcome_state": "blocked", "outcome_message": "A symbol is required."}), 400
        mode_context = _request_value("mode_context", "paper" if config.paper else "live") or ("paper" if config.paper else "live")
        confirmation_value = _request_value("live_confirmation")
        confirmation_state, confirmation_error = _confirmation_state_for_request(
            config,
            mode_context=mode_context,
            requested_action="restart",
            provided_confirmation=confirmation_value,
        )
        if confirmation_error:
            return jsonify(
                _control_response(
                    _blocked_control_action(
                        symbol=symbol,
                        requested_action="restart",
                        mode_context=mode_context,
                        asset_class=infer_asset_class(symbol),
                        confirmation_state=confirmation_state,
                        outcome_message=confirmation_error,
                    )
                )
            )
        action = restart_action_runner(
            config,
            symbol,
            mode="paper" if mode_context == "paper" else "live",
            requested_from="dashboard",
            confirmation_state=confirmation_state,
        )
        return jsonify(_control_response(action))

    return app
