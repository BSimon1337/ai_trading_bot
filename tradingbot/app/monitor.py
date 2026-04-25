from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, jsonify, render_template

from tradingbot.config.settings import BotConfig, infer_asset_class


DEFAULT_REFRESH_SECONDS = 15
DEFAULT_STALE_AFTER_MINUTES = 180
SENSITIVE_KEYWORDS = ("key", "secret", "token", "password", "credential")
VALUE_SOURCE_FILL = "latest_fill"
VALUE_SOURCE_SNAPSHOT_DELTA = "snapshot_delta"
VALUE_SOURCE_UNAVAILABLE = "unavailable"


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


def _clean_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    return str(value)


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
            normalized["timestamp"] = pd.to_datetime(normalized["date"], errors="coerce", utc=True)
        else:
            normalized["timestamp"] = pd.NaT
    else:
        normalized["timestamp"] = pd.to_datetime(normalized["timestamp"], errors="coerce", utc=True)
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


def _parse_instance_timestamp(value: str | None) -> pd.Timestamp | None:
    if not value:
        return None
    timestamp = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(timestamp):
        return None
    return timestamp


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
        last_update_ts = _parse_instance_timestamp(instance.last_updated_at)
        if snapshot_ts is not None:
            fallback_candidates.append((snapshot_ts, instance))
            if snapshot_ts >= cutoff:
                candidates.append((snapshot_ts, instance))
        elif last_update_ts is not None:
            fallback_candidates.append((last_update_ts, instance))
            if last_update_ts >= cutoff:
                candidates.append((last_update_ts, instance))
    ranked = candidates or fallback_candidates
    if not ranked:
        return instances[0]
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def _value_evidence(
    snapshot: SnapshotSummary | None,
    fill: FillSummary | None,
) -> tuple[float, float, str]:
    position_qty = to_float(snapshot.position_qty if snapshot is not None else None)
    fill_qty = to_float(fill.quantity if fill is not None else None)
    fill_notional = to_float(fill.notional_usd if fill is not None else None)
    if fill_qty > 0 and fill_notional > 0:
        unit_value = fill_notional / fill_qty
        return unit_value, position_qty * unit_value, VALUE_SOURCE_FILL

    portfolio_value = to_float(snapshot.portfolio_value if snapshot is not None else None)
    cash = to_float(snapshot.cash if snapshot is not None else None)
    if position_qty > 0 and portfolio_value >= cash:
        held_value = max(portfolio_value - cash, 0.0)
        if held_value > 0:
            return held_value / position_qty, held_value, VALUE_SOURCE_SNAPSHOT_DELTA

    return 0.0, 0.0, VALUE_SOURCE_UNAVAILABLE


def _age_minutes(timestamp: pd.Timestamp | None) -> float | None:
    if timestamp is None or pd.isna(timestamp):
        return None
    return float((datetime.now(timezone.utc) - timestamp.to_pydatetime()).total_seconds() / 60.0)


def _classify_status(
    latest_decision: DecisionSummary | None,
    issues: list[IssueSummary],
    age_minutes: float | None,
    stale_after_minutes: int,
) -> RuntimeStatus:
    if latest_decision is None:
        return RuntimeStatus("no_data", "warning", "No runtime evidence found.", age_minutes)
    live_like = latest_decision.mode in {"active-live", "live"}
    paper_like = latest_decision.mode == "paper"
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
) -> list[IssueSummary]:
    issues = [result.issue for result in read_results if result.issue is not None]
    if age_minutes is not None and age_minutes > stale_after_minutes:
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
        if frame.empty:
            continue
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
    if not snapshot.empty:
        recent_snapshot = snapshot.tail(5).to_dict(orient="records")
        for row in recent_snapshot:
            day_pnl = to_float(row.get("day_pnl"), 0.0)
            if day_pnl < 0:
                issues.append(
                    IssueSummary(
                        timestamp=_utc_now_iso(),
                        severity="info",
                        symbol=_clean_value(row.get("symbol")) or "SYSTEM",
                        category="negative_pnl",
                        message=f"Latest day PnL is negative: {day_pnl:.2f}",
                        source="snapshot",
                    )
                )
                break
    return [issue for issue in _sort_issues([issue for issue in issues if issue is not None])]


def summarize_instance(
    instance: DashboardInstance,
    *,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> DashboardInstance:
    decision_result = safe_read_csv(instance.decision_log_path, source="decisions")
    fill_result = safe_read_csv(instance.fill_log_path, source="fills")
    snapshot_result = safe_read_csv(instance.snapshot_log_path, source="snapshot")
    decisions = normalize_timestamps(decision_result.dataframe)
    fills = normalize_timestamps(fill_result.dataframe)
    snapshot = _normalize_snapshot_frame(snapshot_result.dataframe)

    latest_decision = (
        _row_to_summary(decisions.iloc[-1].to_dict(), DecisionSummary) if not decisions.empty else None
    )
    latest_fill = _row_to_summary(fills.iloc[-1].to_dict(), FillSummary) if not fills.empty else None
    latest_snapshot = (
        _row_to_summary(snapshot.iloc[-1].to_dict(), SnapshotSummary) if not snapshot.empty else None
    )
    last_timestamp = _latest_timestamp(decisions, fills)
    age = _age_minutes(last_timestamp)
    issues = _issues_from_evidence(
        (decision_result, fill_result, snapshot_result),
        decisions,
        fills,
        snapshot,
        age,
        stale_after_minutes,
    )
    status = _classify_status(latest_decision, issues, age, stale_after_minutes)
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
    )


def _instance_payload(instance: DashboardInstance) -> dict[str, Any]:
    latest_decision = instance.latest_decision or DecisionSummary()
    latest_fill = instance.latest_fill or FillSummary()
    latest_snapshot = instance.latest_snapshot or SnapshotSummary()
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
    latest_fill_price, held_value_estimate, held_value_source = _value_evidence(latest_snapshot, latest_fill)
    return {
        "label": instance.label,
        "status": _status_to_dict(instance.status),
        "status_state": instance.status.state,
        "status_severity": instance.status.severity,
        "symbols": list(instance.symbols),
        "asset_classes": list(instance.asset_classes),
        "latest_action": latest_decision.action or "n/a",
        "latest_reason": latest_decision.reason or instance.status.message,
        "latest_mode": latest_decision.mode or "unknown",
        "latest_asset_class": latest_decision.asset_class or (instance.asset_classes[0] if instance.asset_classes else "unknown"),
        "latest_source": latest_decision.action_source or "n/a",
        "latest_update_utc": instance.last_updated_at,
        "heartbeat_age_minutes": instance.status.age_minutes,
        "account_equity": to_float(latest_snapshot.portfolio_value),
        "portfolio_value": to_float(latest_snapshot.portfolio_value),
        "cash": to_float(latest_snapshot.cash),
        "day_pnl": to_float(latest_snapshot.day_pnl),
        "position_qty": to_float(latest_snapshot.position_qty),
        "held_value_estimate": held_value_estimate,
        "held_value_source": held_value_source,
        "latest_fill_price": latest_fill_price,
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
    }


def _aggregate_state(instances: list[DashboardInstance]) -> str:
    states = {instance.status.state for instance in instances}
    if not instances:
        return "no_data"
    for state in ("failed", "blocked", "stale", "no_data"):
        if state in states:
            return state
    if "live" in states:
        return "live"
    if "paper" in states:
        return "paper"
    return "running"


def _build_account_overview(instances: list[DashboardInstance]) -> dict[str, Any]:
    if not instances:
        return {
            "account_equity": 0.0,
            "cash": 0.0,
            "day_pnl": 0.0,
            "active_instances": 0,
            "fills_today": 0,
            "source_instance": "",
            "latest_update_utc": "",
        }

    freshest = _select_authoritative_account_instance(instances)
    if freshest is None:
        return {
            "account_equity": 0.0,
            "cash": 0.0,
            "day_pnl": 0.0,
            "active_instances": len(instances),
            "fills_today": 0,
            "source_instance": "",
            "latest_update_utc": "",
        }
    snapshot = freshest.latest_snapshot or SnapshotSummary()
    latest_update = snapshot.timestamp or freshest.last_updated_at or ""
    return {
        "account_equity": to_float(snapshot.portfolio_value),
        "cash": to_float(snapshot.cash),
        "day_pnl": to_float(snapshot.day_pnl),
        "active_instances": len(instances),
        "fills_today": sum(1 for instance in instances if instance.latest_fill is not None),
        "source_instance": freshest.label,
        "latest_update_utc": latest_update,
    }


def dashboard_status(
    instances: tuple[DashboardInstance, ...] | None = None,
    *,
    config: BotConfig | None = None,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
) -> dict[str, Any]:
    configured = instances if instances is not None else load_monitor_configuration(config=config).instances
    summarized = [summarize_instance(instance, stale_after_minutes=stale_after_minutes) for instance in configured]
    issues = [issue for instance in summarized for issue in instance.issues]
    recent_activity = _collect_recent_activity(summarized)
    payload = {
        "status_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "aggregate_state": _aggregate_state(summarized),
        "account_overview": _build_account_overview(summarized),
        "instances": [_instance_payload(instance) for instance in summarized],
        "issues": [_issue_to_dict(issue) for issue in issues],
        "recent_activity_columns": ["timestamp", "instance_label", "mode", "symbol", "action", "action_source", "quantity", "reason", "result"],
        "recent_activity_rows": recent_activity,
    }
    return redact_sensitive_values(payload)


def create_app(
    *,
    instances: tuple[DashboardInstance, ...] | None = None,
    config: BotConfig | None = None,
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[2] / "templates"))

    def status_payload() -> dict[str, Any]:
        return dashboard_status(instances, config=config, stale_after_minutes=stale_after_minutes)

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

    return app
