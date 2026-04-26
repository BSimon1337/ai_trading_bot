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

from tradingbot.config.settings import BotConfig, infer_asset_class


DEFAULT_REFRESH_SECONDS = 15
DEFAULT_STALE_AFTER_MINUTES = 180
DEFAULT_HISTORY_ISSUE_LIMIT = 5
DEFAULT_ARCHIVE_MARKERS = ("archive", "archived", "history", "historical", "old", "retained")
SENSITIVE_KEYWORDS = ("key", "secret", "token", "password", "credential")
VALUE_SOURCE_FILL = "latest_fill"
VALUE_SOURCE_SNAPSHOT_DELTA = "snapshot_delta"
VALUE_SOURCE_UNAVAILABLE = "unavailable"
DEFAULT_HEADLINE_PREVIEW_LIMIT = 3
DEFAULT_SENTIMENT_TREND_LIMIT = 5


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
    observed_at: str = ""
    decision_mode: str = ""


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
    stale_after_minutes = _safe_int(os.getenv("MONITOR_STALE_AFTER_MINUTES"), DEFAULT_STALE_AFTER_MINUTES)
    historical_issue_limit = _safe_int(os.getenv("MONITOR_HISTORICAL_ISSUE_LIMIT"), DEFAULT_HISTORY_ISSUE_LIMIT)
    dashboard_host = os.getenv("MONITOR_HOST", "127.0.0.1").strip() or "127.0.0.1"
    tray_enabled = os.getenv("MONITOR_TRAY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}
    archive_markers = tuple(
        marker.strip().lower()
        for marker in os.getenv("MONITOR_ARCHIVE_MARKERS", ",".join(DEFAULT_ARCHIVE_MARKERS)).split(",")
        if marker.strip()
    ) or DEFAULT_ARCHIVE_MARKERS
    return MonitorConfiguration(
        dashboard_host=dashboard_host,
        dashboard_port=dashboard_port,
        refresh_seconds=refresh_seconds,
        stale_after_minutes=stale_after_minutes,
        historical_issue_limit=historical_issue_limit,
        archive_markers=archive_markers,
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


def _infer_sentiment_availability_state(
    source: str,
    label: str,
    headline_count: int,
    explicit_state: str = "",
) -> str:
    if explicit_state:
        return explicit_state
    if source == "neutral_fallback":
        return "neutral_fallback"
    if source == "local_fixture":
        return "local_fixture_scored" if label else "local_fixture_unavailable"
    if source == "external" and headline_count > 0 and label:
        return "news_scored"
    if headline_count <= 0:
        return "no_headlines"
    if label:
        return "scored"
    return "unavailable"


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
    return SentimentSnapshot(
        symbol=summary.symbol,
        label=summary.sentiment_label,
        probability=probability,
        source=summary.sentiment_source,
        availability_state=availability_state,
        is_fallback=to_bool(summary.sentiment_is_fallback, default=summary.sentiment_source == "neutral_fallback"),
        observed_at=summary.sentiment_observed_at or summary.timestamp,
        decision_mode=summary.mode,
    )


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
        is_stale=False,
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
    *,
    evidence_scope: str = "active",
) -> list[IssueSummary]:
    issues: list[IssueSummary] = []
    if evidence_scope != "historical":
        issues.extend(result.issue for result in read_results if result.issue is not None)
    if evidence_scope != "historical" and age_minutes is not None and age_minutes > stale_after_minutes:
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
) -> list[NoteSummary]:
    del decisions, fills
    notes: list[NoteSummary] = []
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
    notes = _notes_from_evidence(active_decisions, active_fills, active_snapshot)
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
        notes=tuple(notes),
        evidence_scope=evidence_scope,
        historical_issues=tuple(historical_issues),
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
    held_value = held_value_estimate if held_value_source != VALUE_SOURCE_UNAVAILABLE else None
    broker_rejection_count = 0
    for frame in (decisions, fills):
        if frame.empty:
            continue
        for row in frame.to_dict(orient="records"):
            reason = str(row.get("reason", ""))
            result = str(row.get("result", ""))
            if result in {"rejected", "canceled"} or reason.startswith("broker_"):
                broker_rejection_count += 1
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
        "last_decision_utc": latest_decision.timestamp or "",
        "last_fill_utc": latest_fill.timestamp or "",
        "heartbeat_age_minutes": instance.status.age_minutes,
        "broker_rejection_count": broker_rejection_count,
        "evidence_scope": instance.evidence_scope,
        "historical_issue_count": len(instance.historical_issues),
        "historical_issues": [_issue_to_dict(issue) for issue in instance.historical_issues],
        "account_equity": to_float(latest_snapshot.portfolio_value),
        "portfolio_value": to_float(latest_snapshot.portfolio_value),
        "cash": to_float(latest_snapshot.cash),
        "day_pnl": to_float(latest_snapshot.day_pnl),
        "position_qty": to_float(latest_snapshot.position_qty),
        "held_value": held_value,
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
        "notes": [_note_to_dict(note) for note in instance.notes],
    }


def _aggregate_state(instances: list[DashboardInstance]) -> str:
    active_instances = [instance for instance in instances if instance.evidence_scope != "historical"]
    considered = active_instances or instances
    states = {instance.status.state for instance in considered}
    if not considered:
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
    latest_update = snapshot.timestamp or freshest.last_updated_at or ""
    latest_update_ts = _parse_instance_timestamp(latest_update)
    is_stale = True if latest_update_ts is None else (_age_minutes(latest_update_ts) or 0.0) > DEFAULT_STALE_AFTER_MINUTES
    instances_with_fills = sum(1 for instance in active_instances if instance.latest_fill is not None)
    return {
        "account_equity": to_float(snapshot.portfolio_value),
        "cash": to_float(snapshot.cash),
        "day_pnl": to_float(snapshot.day_pnl),
        "active_instances": len(active_instances),
        "instances_count": len(active_instances),
        "fills_today": instances_with_fills,
        "instances_with_fills": instances_with_fills,
        "source_instance": freshest.label,
        "latest_update_utc": latest_update,
        "is_stale": is_stale,
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
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
) -> dict[str, Any]:
    configured = instances if instances is not None else load_monitor_configuration(config=config).instances
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
    issues = [issue for instance in display_instances for issue in instance.issues]
    notes = [note for instance in display_instances for note in instance.notes]
    recent_activity = _collect_recent_activity(display_instances)
    payload = {
        "status_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "aggregate_state": _aggregate_state(summarized),
        "account_overview": _build_account_overview(summarized),
        "historical_context": _build_historical_context(
            summarized,
            stale_after_minutes=stale_after_minutes,
            historical_issue_limit=historical_issue_limit,
        ),
        "instances": [_instance_payload(instance) for instance in display_instances],
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
    stale_after_minutes: int = DEFAULT_STALE_AFTER_MINUTES,
    historical_issue_limit: int = DEFAULT_HISTORY_ISSUE_LIMIT,
    archive_markers: tuple[str, ...] = DEFAULT_ARCHIVE_MARKERS,
    refresh_seconds: int = DEFAULT_REFRESH_SECONDS,
) -> Flask:
    app = Flask(__name__, template_folder=str(Path(__file__).resolve().parents[2] / "templates"))

    def status_payload() -> dict[str, Any]:
        return dashboard_status(
            instances,
            config=config,
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

    return app
