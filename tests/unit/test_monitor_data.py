from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tests.conftest import make_bot_config
from tests.fixtures.monitor.build_fixtures import (
    create_monitor_fixture,
    recent_control_action,
    recent_decision,
    runtime_registry_lifecycle_event,
    runtime_registry_runtime,
    write_decisions,
    write_malformed_csv,
    write_runtime_registry,
)
from tradingbot.app.monitor import (
    DEFAULT_HEADLINE_PREVIEW_LIMIT,
    VALUE_SOURCE_FILL_DELTA,
    VALUE_SOURCE_SNAPSHOT_DELTA,
    _normalize_snapshot_frame,
    _filter_active_evidence,
    _headline_evidence_preview,
    _select_authoritative_account_instance,
    _sentiment_snapshot,
    _sentiment_trend,
    _value_evidence,
    DecisionSummary,
    DashboardInstance,
    SnapshotSummary,
    discover_monitor_instances,
    dashboard_status,
    load_monitor_configuration,
    normalize_timestamps,
    redact_sensitive_values,
    safe_read_csv,
    sanitize_symbol_for_path,
    summarize_instance,
    to_float,
    to_int,
)


def _sentiment_row(
    symbol: str = "BTC/USD",
    **overrides,
) -> dict[str, object]:
    row = recent_decision(
        symbol=symbol,
        mode="live",
        sentiment_source="external",
        sentiment_probability="0.82",
        sentiment_label="positive",
        sentiment_availability_state="news_scored",
        sentiment_is_fallback="false",
        sentiment_observed_at=datetime.now(timezone.utc).isoformat(),
        headline_count="4",
        headline_preview='["BTC rallies on ETF optimism","Fed cools rate fears","Crypto volumes rise","Institutions return"]',
        sentiment_window_start="2026-04-23",
        sentiment_window_end="2026-04-26",
    )
    row.update(overrides)
    return row


def test_safe_read_csv_returns_empty_frame_and_issue_for_missing_file(tmp_path):
    result = safe_read_csv(tmp_path / "missing.csv", source="decisions")

    assert result.dataframe.empty
    assert result.issue is not None
    assert result.issue.category == "no_data"
    assert "missing.csv" in result.issue.message


def test_safe_read_csv_returns_empty_frame_and_issue_for_malformed_file(tmp_path):
    path = write_malformed_csv(tmp_path / "bad.csv")

    result = safe_read_csv(path, source="decisions")

    assert result.dataframe.empty
    assert result.issue is not None
    assert result.issue.category == "malformed_csv"


def test_safe_read_csv_recovers_rows_from_mixed_schema_file_when_possible(tmp_path):
    path = tmp_path / "mixed.csv"
    path.write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,quantity,portfolio_value,cash,reason,result",
                "2026-04-30T00:00:00+00:00,live,SPY,stock,hold,model,0,100,100,hold,skipped",
                "2026-04-30T00:01:00+00:00,live,SPY,stock,hold,model,,,,,,,,extra",
                "2026-04-30T00:02:00+00:00,live,SPY,stock,hold,model,0,101,100,hold,skipped",
            ]
        ),
        encoding="utf-8",
    )

    result = safe_read_csv(path, source="decisions")

    assert result.issue is None
    assert len(result.dataframe) == 2


def test_safe_read_csv_reads_valid_decision_file(tmp_path):
    path = write_decisions(tmp_path / "decisions.csv", [recent_decision(symbol="BTC/USD")])

    result = safe_read_csv(path, source="decisions")

    assert result.issue is None
    assert list(result.dataframe["symbol"]) == ["BTC/USD"]


def test_normalize_timestamps_sorts_rows_by_timestamp():
    frame = pd.DataFrame(
        [
            {"timestamp": "2026-04-18T12:01:00+00:00", "symbol": "BTC/USD"},
            {"timestamp": "2026-04-18T12:00:00+00:00", "symbol": "ETH/USD"},
        ]
    )

    normalized = normalize_timestamps(frame)

    assert list(normalized["symbol"]) == ["ETH/USD", "BTC/USD"]


def test_normalize_snapshot_frame_parses_mixed_date_and_timestamp_values():
    frame = pd.DataFrame(
        [
            {"date": "2026-04-25", "symbol": "BTC/USD", "portfolio_value": "99.93", "cash": "25.97", "position_qty": "0.000193", "day_pnl": "0.0"},
            {"date": "2026-04-29T20:56:00.159465-04:00", "symbol": "BTC/USD", "portfolio_value": "99.14", "cash": "59.915432", "position_qty": "0.00026", "day_pnl": "0.0"},
        ]
    )

    normalized = _normalize_snapshot_frame(frame)

    assert normalized["timestamp"].notna().all()
    assert normalized.iloc[-1]["portfolio_value"] == "99.14"


def test_numeric_helpers_use_defaults_for_bad_values():
    assert to_float("12.5") == 12.5
    assert to_float("nope", default=7.0) == 7.0
    assert to_int("3") == 3
    assert to_int("nope", default=9) == 9


def test_sentiment_snapshot_parses_current_runtime_evidence_fields():
    summary = DecisionSummary(**_sentiment_row())

    snapshot = _sentiment_snapshot(summary)

    assert snapshot.symbol == "BTC/USD"
    assert snapshot.label == "positive"
    assert snapshot.probability == 0.82
    assert snapshot.source == "external"
    assert snapshot.availability_state == "news_scored"
    assert snapshot.is_fallback is False
    assert snapshot.observed_at


def test_sentiment_snapshot_distinguishes_fallback_neutral_from_real_neutral():
    fallback_summary = DecisionSummary(
        **_sentiment_row(
            sentiment_source="neutral_fallback",
            sentiment_probability="0.0",
            sentiment_label="neutral",
            sentiment_availability_state="",
            sentiment_is_fallback="true",
            headline_count="0",
            headline_preview="[]",
        )
    )
    real_neutral_summary = DecisionSummary(
        **_sentiment_row(
            sentiment_source="external",
            sentiment_probability="0.61",
            sentiment_label="neutral",
            sentiment_availability_state="",
            sentiment_is_fallback="false",
            headline_count="2",
            headline_preview='["Calmer CPI data","Large caps steady"]',
        )
    )

    fallback = _sentiment_snapshot(fallback_summary)
    real_neutral = _sentiment_snapshot(real_neutral_summary)

    assert fallback.availability_state == "neutral_fallback"
    assert fallback.is_fallback is True
    assert real_neutral.availability_state == "news_scored"
    assert real_neutral.is_fallback is False


def test_headline_evidence_preview_is_bounded_for_dashboard_display():
    summary = DecisionSummary(**_sentiment_row())

    preview = _headline_evidence_preview(summary)

    assert preview.headline_count == 4
    assert len(preview.headlines) == DEFAULT_HEADLINE_PREVIEW_LIMIT
    assert preview.headlines[0] == "BTC rallies on ETF optimism"
    assert preview.window_start == "2026-04-23"
    assert preview.window_end == "2026-04-26"


def test_sentiment_trend_helper_returns_recent_bounded_entries():
    frame = pd.DataFrame(
        [
            _sentiment_row(timestamp="2026-04-26T12:00:00+00:00", sentiment_label="negative", sentiment_probability="0.71"),
            _sentiment_row(timestamp="2026-04-26T12:15:00+00:00", sentiment_label="neutral", sentiment_probability="0.55"),
            _sentiment_row(timestamp="2026-04-26T12:30:00+00:00", sentiment_label="positive", sentiment_probability="0.83"),
        ]
    )

    trend = _sentiment_trend(frame, limit=2)

    assert len(trend) == 2
    assert trend[0].label == "neutral"
    assert trend[1].label == "positive"
    assert trend[1].availability_state == "news_scored"


def test_dashboard_status_extracts_current_per_symbol_sentiment_snapshot(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(
                symbol="BTC/USD",
                timestamp="2026-04-26T15:00:00+00:00",
                sentiment_label="positive",
                sentiment_probability="0.91",
                sentiment_source="external",
                sentiment_availability_state="news_scored",
                sentiment_is_fallback="false",
            )
        ],
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["sentiment_label"] == "positive"
    assert item["sentiment_probability"] == 0.91
    assert item["sentiment_source"] == "external"
    assert item["sentiment_availability_state"] == "news_scored"
    assert item["sentiment_is_fallback"] is False
    assert item["sentiment_last_updated_utc"]


def test_load_monitor_configuration_merges_runtime_registry_state(tmp_path, monkeypatch):
    runtime_registry_path = tmp_path / "runtime" / "runtime_registry.json"
    write_runtime_registry(
        runtime_registry_path,
        {
            "registry_version": 1,
            "updated_at_utc": "2026-04-28T02:00:00+00:00",
            "managed_runtimes": [
                {
                    "symbol": "BTC/USD",
                    "instance_label": "BTC/USD",
                    "mode": "live",
                    "lifecycle_state": "running",
                    "session_id": "session-btc",
                    "pid": 2468,
                    "started_at_utc": "2026-04-28T01:55:00+00:00",
                    "last_seen_utc": "2026-04-28T02:00:00+00:00",
                    "decision_log_path": "logs/paper_validation_btcusd/decisions.csv",
                    "fill_log_path": "logs/paper_validation_btcusd/fills.csv",
                    "snapshot_log_path": "logs/paper_validation_btcusd/daily_snapshot.csv",
                }
            ],
            "recent_sessions": [],
            "lifecycle_events": [],
            "recent_control_actions": [
                recent_control_action(symbol="BTC/USD", requested_action="start", mode_context="live"),
            ],
        },
    )
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(runtime_registry_path))

    config = load_monitor_configuration(symbols=("BTC/USD",))
    instance = config.instances[0]

    assert config.runtime_registry_path == runtime_registry_path
    assert len(config.recent_control_actions) == 1
    assert instance.runtime_state == "running"
    assert instance.runtime_session_id == "session-btc"
    assert instance.runtime_pid == 2468
    assert instance.runtime_started_at_utc == "2026-04-28T01:55:00+00:00"


def test_load_monitor_configuration_uses_configured_observability_limits(tmp_path, monkeypatch):
    runtime_registry_path = tmp_path / "runtime" / "runtime_registry.json"
    write_runtime_registry(
        runtime_registry_path,
        {
            "registry_version": 1,
            "updated_at_utc": "2026-04-30T00:46:00+00:00",
            "managed_runtimes": [runtime_registry_runtime(symbol="BTC/USD")],
            "recent_sessions": [],
            "lifecycle_events": [],
            "recent_control_actions": [],
        },
    )
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(runtime_registry_path))
    config = make_bot_config(
        symbols=("BTC/USD",),
        monitor_runtime_event_limit=7,
        monitor_active_warning_limit=3,
    )

    monitor_config = load_monitor_configuration(config=config, symbols=("BTC/USD",))

    assert monitor_config.runtime_event_limit == 7
    assert monitor_config.active_warning_limit == 3


def test_dashboard_status_overlays_reconciled_runtime_truth_from_registry(tmp_path, monkeypatch):
    runtime_registry_path = tmp_path / "runtime" / "runtime_registry.json"
    write_runtime_registry(
        runtime_registry_path,
        {
            "registry_version": 1,
            "updated_at_utc": "2026-04-30T00:46:00+00:00",
            "managed_runtimes": [
                runtime_registry_runtime(
                    symbol="BTC/USD",
                    session_id="session-btc",
                    lifecycle_state="running",
                    pid=2468,
                )
            ],
            "recent_sessions": [],
            "lifecycle_events": [runtime_registry_lifecycle_event(symbol="BTC/USD", session_id="session-btc")],
            "recent_control_actions": [],
        },
    )
    monkeypatch.setattr("tradingbot.app.runtime_manager._is_process_running", lambda pid: False)
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    config = make_bot_config(symbols=("BTC/USD",), runtime_registry_path=str(runtime_registry_path))

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="running",
                runtime_mode_context="live",
                runtime_status_message="Runtime is running.",
                runtime_session_id="session-btc",
                runtime_pid=2468,
            ),
        ),
        config=config,
    )
    item = payload["instances"][0]

    assert item["runtime_state"] == "failed"
    assert item["status"]["state"] == "failed"
    assert item["runtime_status_message"] == "Runtime process exited unexpectedly."


def test_summarize_instance_preserves_runtime_registry_metadata(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
        runtime_state="running",
        runtime_status_message="running",
        runtime_session_id="session-btc",
        runtime_pid=2468,
        runtime_started_at_utc="2026-04-28T01:55:00+00:00",
        runtime_last_seen_utc="2026-04-28T02:00:00+00:00",
        last_lifecycle_event="started",
        is_fresh_runtime_session=True,
    )

    summary = summarize_instance(instance)

    assert summary.runtime_state == "running"
    assert summary.runtime_session_id == "session-btc"
    assert summary.runtime_pid == 2468
    assert summary.runtime_started_at_utc == "2026-04-28T01:55:00+00:00"
    assert summary.runtime_last_seen_utc == "2026-04-28T02:00:00+00:00"
    assert summary.last_lifecycle_event == "started"
    assert summary.is_fresh_runtime_session is True


def test_dashboard_status_includes_runtime_registry_fields_on_instance_payload(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="running",
                runtime_status_message="Runtime is running.",
                runtime_session_id="session-btc",
                runtime_pid=2468,
                runtime_started_at_utc="2026-04-28T01:55:00+00:00",
                runtime_last_seen_utc="2026-04-28T02:00:00+00:00",
                last_lifecycle_event="running",
                is_fresh_runtime_session=True,
            ),
        )
    )
    item = payload["instances"][0]

    assert item["runtime_state"] == "running"
    assert item["runtime_status_message"] == "Runtime is running."
    assert item["runtime_session_id"] == "session-btc"
    assert item["runtime_pid"] == 2468
    assert item["runtime_started_at_utc"] == "2026-04-28T01:55:00+00:00"
    assert item["runtime_last_seen_utc"] == "2026-04-28T02:00:00+00:00"
    assert item["last_lifecycle_event"] == "running"
    assert item["is_fresh_runtime_session"] is True
    assert item["status_reason"] == "Runtime is running."
    assert item["recent_runtime_events"]
    assert any(event["runtime_phase"] == "running" for event in item["recent_runtime_events"])
    assert item["active_warnings"] == []
    assert item["latest_order_lifecycle"]["lifecycle_state"] == "no_order"
    assert item["freshness_state"] in {"current", "provisional", "stale", "historical", "unavailable"}
    assert item["freshness_explanation"]


def test_dashboard_status_includes_control_availability_fields_per_instance(tmp_path):
    running_paths = create_monitor_fixture(tmp_path / "running", "healthy", symbol="BTC/USD")
    stopped_paths = create_monitor_fixture(tmp_path / "stopped", "stale", symbol="SPY")

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=running_paths["decisions"],
                fill_log_path=running_paths["fills"],
                snapshot_log_path=running_paths["snapshot"],
                runtime_state="running",
                runtime_mode_context="live",
            ),
            DashboardInstance(
                label="SPY",
                symbols=("SPY",),
                asset_classes=("stock",),
                decision_log_path=stopped_paths["decisions"],
                fill_log_path=stopped_paths["fills"],
                snapshot_log_path=stopped_paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="paper",
            ),
        )
    )

    running_item = next(item for item in payload["instances"] if item["label"] == "BTC/USD")
    stopped_item = next(item for item in payload["instances"] if item["label"] == "SPY")

    assert running_item["control_asset_class"] == "crypto"
    assert running_item["control_mode_context"] == "live"
    assert running_item["control_runtime_state"] == "running"
    assert running_item["can_start"] is False
    assert running_item["can_stop"] is True
    assert running_item["can_restart"] is True
    assert running_item["requires_live_confirmation"] is False

    assert stopped_item["control_asset_class"] == "stock"
    assert stopped_item["control_mode_context"] == "paper"
    assert stopped_item["control_runtime_state"] == "stopped"
    assert stopped_item["can_start"] is True
    assert stopped_item["can_stop"] is False
    assert stopped_item["can_restart"] is True
    assert stopped_item["requires_live_confirmation"] is False


def test_dashboard_status_includes_live_and_paper_control_confirmation_messages(tmp_path):
    live_paths = create_monitor_fixture(tmp_path / "live", "healthy", symbol="BTC/USD")
    paper_paths = create_monitor_fixture(tmp_path / "paper", "healthy", symbol="SPY")
    config = make_bot_config(
        paper=False,
        live_trading_enabled=True,
        live_run_confirmation="CONFIRM",
        live_confirmation_token="CONFIRM",
    )

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=live_paths["decisions"],
                fill_log_path=live_paths["fills"],
                snapshot_log_path=live_paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="live",
            ),
            DashboardInstance(
                label="SPY",
                symbols=("SPY",),
                asset_classes=("stock",),
                decision_log_path=paper_paths["decisions"],
                fill_log_path=paper_paths["fills"],
                snapshot_log_path=paper_paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="paper",
            ),
        ),
        config=config,
    )

    live_item = next(item for item in payload["instances"] if item["label"] == "BTC/USD")
    paper_item = next(item for item in payload["instances"] if item["label"] == "SPY")

    assert live_item["control_confirmation_hint"] == "Live controls use this trusted local dashboard session."
    assert paper_item["control_confirmation_hint"] == "Live controls use this trusted local dashboard session."


def test_dashboard_status_prefers_monitor_mode_for_stopped_runtime_controls(tmp_path):
    paper_paths = create_monitor_fixture(tmp_path / "paper", "healthy", symbol="SPY")
    config = make_bot_config(
        paper=False,
        live_trading_enabled=True,
        symbols=("SPY",),
    )

    payload = dashboard_status(
        (
            DashboardInstance(
                label="SPY",
                symbols=("SPY",),
                asset_classes=("stock",),
                decision_log_path=paper_paths["decisions"],
                fill_log_path=paper_paths["fills"],
                snapshot_log_path=paper_paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="paper",
            ),
        ),
        config=config,
    )

    item = payload["instances"][0]

    assert item["control_mode_context"] == "live"
    assert item["control_confirmation_hint"] == "Live controls use this trusted local dashboard session."


def test_dashboard_status_includes_recent_control_actions_from_runtime_registry(tmp_path, monkeypatch):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    runtime_registry_path = tmp_path / "runtime" / "runtime_registry.json"
    write_runtime_registry(
        runtime_registry_path,
        {
            "registry_version": 1,
            "updated_at_utc": "2026-04-28T02:00:00+00:00",
            "managed_runtimes": [],
            "recent_sessions": [],
            "lifecycle_events": [],
            "recent_control_actions": [
                recent_control_action(
                    symbol="SPY",
                    requested_action="start",
                    mode_context="paper",
                    requested_at_utc="2026-04-28T01:59:00+00:00",
                ),
                recent_control_action(
                    symbol="BTC/USD",
                    requested_action="restart",
                    mode_context="live",
                    requested_at_utc="2026-04-28T02:00:00+00:00",
                ),
            ],
        },
    )
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(runtime_registry_path))

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
            ),
        )
    )

    assert payload["latest_control_updated_at_utc"] == "2026-04-28T02:00:00+00:00"
    assert [item["symbol"] for item in payload["recent_control_actions"]] == ["BTC/USD", "SPY"]
    assert payload["recent_control_actions"][0]["requested_action"] == "restart"


def test_dashboard_status_exposes_mixed_asset_recent_control_history_with_counts(tmp_path, monkeypatch):
    paths = create_monitor_fixture(tmp_path / "btc", "no_data", symbol="BTC/USD")
    runtime_registry_path = tmp_path / "runtime" / "runtime_registry.json"
    write_runtime_registry(
        runtime_registry_path,
        {
            "registry_version": 1,
            "updated_at_utc": "2026-04-28T02:10:00+00:00",
            "managed_runtimes": [],
            "recent_sessions": [],
            "lifecycle_events": [],
            "recent_control_actions": [
                recent_control_action(
                    symbol="SPY",
                    requested_action="start",
                    mode_context="paper",
                    requested_at_utc="2026-04-28T02:01:00+00:00",
                ),
                recent_control_action(
                    symbol="BTC/USD",
                    requested_action="restart",
                    mode_context="live",
                    requested_at_utc="2026-04-28T02:09:00+00:00",
                    outcome_state="blocked",
                ),
            ],
        },
    )
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(runtime_registry_path))

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="live",
            ),
            DashboardInstance(
                label="SPY",
                symbols=("SPY",),
                asset_classes=("stock",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="stopped",
                runtime_mode_context="paper",
            ),
        )
    )

    assert payload["recent_control_activity_count"] == 2
    assert payload["latest_control_updated_at_utc"] == "2026-04-28T02:10:00+00:00"
    assert payload["recent_control_actions"][0]["symbol"] == "BTC/USD"
    assert payload["recent_control_actions"][0]["asset_class"] == "crypto"
    assert payload["recent_control_actions"][1]["symbol"] == "SPY"
    assert payload["recent_control_actions"][1]["asset_class"] == "stock"


def test_dashboard_status_keeps_stop_and_failure_runtime_messages_visible(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="stopped",
                runtime_status_message="Runtime stopped by operator.",
                runtime_session_id="session-btc",
                runtime_pid=None,
                runtime_started_at_utc="2026-04-28T01:55:00+00:00",
                runtime_last_seen_utc="2026-04-28T02:10:00+00:00",
                last_lifecycle_event="stopped",
                is_fresh_runtime_session=False,
            ),
        )
    )
    item = payload["instances"][0]

    assert item["runtime_state"] == "stopped"
    assert item["runtime_status_message"] == "Runtime stopped by operator."
    assert item["last_lifecycle_event"] == "stopped"


def test_dashboard_status_distinguishes_stopped_runtime_from_stale_logs(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "stale", symbol="BTC/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="stopped",
                runtime_status_message="Runtime stopped by operator.",
                runtime_session_id="session-btc",
                runtime_started_at_utc="2026-04-28T01:55:00+00:00",
                runtime_last_seen_utc="2026-04-28T02:10:00+00:00",
                last_lifecycle_event="stopped",
            ),
        )
    )
    item = payload["instances"][0]

    assert item["status"]["state"] == "stopped"
    assert item["status"]["message"] == "Runtime stopped by operator."
    assert payload["aggregate_state"] == "stopped"


def test_dashboard_status_keeps_stopped_runtime_history_as_note_not_active_stale_issue(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "stale", symbol="BTC/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="stopped",
                runtime_status_message="Runtime stopped by operator.",
                runtime_session_id="session-btc",
                runtime_started_at_utc="2026-04-28T01:55:00+00:00",
                runtime_last_seen_utc="2026-04-28T02:10:00+00:00",
                last_lifecycle_event="stopped",
            ),
        )
    )
    item = payload["instances"][0]

    assert item["status"]["state"] == "stopped"
    assert not any(issue["category"] == "stale_data" for issue in item["issues"])
    assert any(note["category"] == "historical_runtime_evidence" for note in item["notes"])


def test_dashboard_status_prefers_fresh_runtime_session_over_older_failed_logs(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "failed", symbol="BTC/USD")
    runtime_started_at = (datetime.now(timezone.utc) + pd.Timedelta(minutes=1)).isoformat()
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="running",
                runtime_status_message="Runtime is running.",
                runtime_session_id="session-btc-new",
                runtime_pid=4567,
                runtime_started_at_utc=runtime_started_at,
                runtime_last_seen_utc=runtime_started_at,
                last_lifecycle_event="restarted",
                is_fresh_runtime_session=True,
            ),
        )
    )
    item = payload["instances"][0]

    assert item["status"]["state"] == "running"
    assert item["runtime_status_message"] == "Runtime is running."
    assert item["last_lifecycle_event"] == "restarted"


def test_dashboard_status_prefers_runtime_mode_context_over_stale_system_mode(tmp_path):
    paths = create_monitor_fixture(tmp_path / "spy", "no_data", symbol="SPY")
    Path(paths["decisions"]).write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,quantity,portfolio_value,cash,reason,result",
                "2026-04-30T17:43:51+00:00,paper,SYSTEM,system,hold,guardrail,,,,,0,,,runtime started,started",
            ]
        ),
        encoding="utf-8",
    )
    payload = dashboard_status(
        (
            DashboardInstance(
                label="SPY",
                symbols=("SPY",),
                asset_classes=("stock",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="running",
                runtime_mode_context="live",
                runtime_status_message="Runtime is running.",
            ),
        )
    )
    item = payload["instances"][0]

    assert item["status_state"] == "live"
    assert item["latest_mode"] == "live"
    assert item["runtime_mode_context"] == "live"


def test_dashboard_status_distinguishes_fallback_neutral_from_real_neutral(tmp_path):
    fallback_paths = create_monitor_fixture(tmp_path / "fallback", "healthy", symbol="BTC/USD")
    real_paths = create_monitor_fixture(tmp_path / "real", "healthy", symbol="ETH/USD")
    write_decisions(
        fallback_paths["decisions"],
        [
            _sentiment_row(
                symbol="BTC/USD",
                sentiment_source="neutral_fallback",
                sentiment_label="neutral",
                sentiment_probability="0.0",
                sentiment_availability_state="",
                sentiment_is_fallback="true",
                headline_count="0",
                headline_preview="[]",
            )
        ],
    )
    write_decisions(
        real_paths["decisions"],
        [
            _sentiment_row(
                symbol="ETH/USD",
                sentiment_source="external",
                sentiment_label="neutral",
                sentiment_probability="0.62",
                sentiment_availability_state="",
                sentiment_is_fallback="false",
                headline_count="2",
                headline_preview='["Macro steadies","Volumes normalize"]',
            )
        ],
    )

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=fallback_paths["decisions"],
                fill_log_path=fallback_paths["fills"],
                snapshot_log_path=fallback_paths["snapshot"],
            ),
            DashboardInstance(
                label="ETH/USD",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=real_paths["decisions"],
                fill_log_path=real_paths["fills"],
                snapshot_log_path=real_paths["snapshot"],
            ),
        )
    )

    fallback_item = next(item for item in payload["instances"] if item["label"] == "BTC/USD")
    real_item = next(item for item in payload["instances"] if item["label"] == "ETH/USD")

    assert fallback_item["sentiment_availability_state"] == "neutral_fallback"
    assert fallback_item["sentiment_is_fallback"] is True
    assert real_item["sentiment_availability_state"] == "news_scored"
    assert real_item["sentiment_is_fallback"] is False


def test_dashboard_status_uses_last_valid_sentiment_during_guardrail_lockout(tmp_path):
    paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(
                symbol="ETH/USD",
                timestamp="2026-04-26T15:00:00+00:00",
                action="buy",
                action_source="model",
                sentiment_label="positive",
                sentiment_probability="0.88",
                sentiment_source="external",
                sentiment_availability_state="news_scored",
                sentiment_is_fallback="false",
                reason="submitted",
                result="submitted",
            ),
            recent_decision(
                symbol="ETH/USD",
                timestamp="2026-04-26T15:15:00+00:00",
                mode="live",
                asset_class="crypto",
                action="hold",
                action_source="guardrail",
                sentiment_source="",
                sentiment_probability="",
                sentiment_label="",
                sentiment_availability_state="",
                sentiment_is_fallback="",
                sentiment_observed_at="",
                headline_count="",
                headline_preview="",
                sentiment_window_start="",
                sentiment_window_end="",
                quantity="0",
                portfolio_value="99.24",
                cash="99.24",
                reason="max_consecutive_losses_lockout_until_next_day_3",
                result="skipped",
            ),
        ],
    )
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["latest_reason"] == "max_consecutive_losses_lockout_until_next_day_3"
    assert item["sentiment_label"] == "positive"
    assert item["sentiment_probability"] == 0.88
    assert item["sentiment_availability_state"] == "news_scored"


def test_dashboard_status_exposes_bounded_headline_preview_per_instance(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(
                symbol="BTC/USD",
                headline_count="6",
                headline_preview='["Headline 1","Headline 2","Headline 3","Headline 4","Headline 5"]',
            )
        ],
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["headline_count"] == 6
    assert item["headline_preview"] == ["Headline 1", "Headline 2", "Headline 3"]
    assert item["sentiment_headline_source_window"]["window_start"] == "2026-04-23"
    assert item["sentiment_headline_source_window"]["window_end"] == "2026-04-26"


def test_dashboard_status_exposes_recent_sentiment_trend_entries(tmp_path):
    paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(symbol="ETH/USD", timestamp="2026-04-26T14:00:00+00:00", sentiment_label="negative", sentiment_probability="0.72"),
            _sentiment_row(symbol="ETH/USD", timestamp="2026-04-26T14:15:00+00:00", sentiment_label="neutral", sentiment_probability="0.53"),
            _sentiment_row(symbol="ETH/USD", timestamp="2026-04-26T14:30:00+00:00", sentiment_label="positive", sentiment_probability="0.88"),
        ],
    )
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    trend = payload["instances"][0]["sentiment_trend"]

    assert len(trend) == 3
    assert trend[0]["label"] == "negative"
    assert trend[-1]["label"] == "positive"
    assert trend[-1]["availability_state"] == "news_scored"


def test_dashboard_status_marks_stale_sentiment_state_when_observed_at_is_old(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(
                symbol="BTC/USD",
                timestamp="2026-04-26T15:00:00+00:00",
                sentiment_observed_at="2026-04-26T10:00:00+00:00",
                sentiment_label="positive",
                sentiment_source="external",
                sentiment_availability_state="news_scored",
                sentiment_is_fallback="false",
            )
        ],
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["sentiment_is_stale"] is True
    assert item["sentiment_availability_state"] == "stale_news_scored"
    assert "stale" in item["sentiment_state_message"].lower()


def test_dashboard_status_handles_no_headline_sentiment_state_cleanly(tmp_path):
    paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    write_decisions(
        paths["decisions"],
        [
            _sentiment_row(
                symbol="ETH/USD",
                sentiment_source="external",
                sentiment_label="neutral",
                sentiment_probability="0.0",
                sentiment_availability_state="",
                sentiment_is_fallback="false",
                headline_count="0",
                headline_preview="[]",
            )
        ],
    )
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["headline_count"] == 0
    assert item["headline_preview"] == []
    assert item["sentiment_availability_state"] == "no_headlines"
    assert "No recent headlines" in item["sentiment_state_message"]


def test_redact_sensitive_values_recurses_without_changing_safe_values():
    payload = {
        "api_key": "abc",
        "nested": {"API_SECRET": "def", "symbol": "BTC/USD"},
        "items": [{"token": "ghi"}, {"mode": "live"}],
    }

    redacted = redact_sensitive_values(payload)

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["nested"]["API_SECRET"] == "[REDACTED]"
    assert redacted["nested"]["symbol"] == "BTC/USD"
    assert redacted["items"][0]["token"] == "[REDACTED]"
    assert redacted["items"][1]["mode"] == "live"


def test_discover_monitor_instances_handles_slash_crypto_symbols(tmp_path):
    instances = discover_monitor_instances(symbols=("F", "BTC/USD", "ETH-USDC"), base_dir=tmp_path)

    labels = [instance.label for instance in instances]
    paths = [instance.decision_log_path for instance in instances]

    assert labels == ["F", "BTC/USD", "ETH-USDC"]
    assert instances[1].asset_classes == ("crypto",)
    assert paths[1] == tmp_path / "paper_validation_btcusd" / "decisions.csv"
    assert paths[2] == tmp_path / "paper_validation_ethusdc" / "decisions.csv"


def test_load_monitor_configuration_uses_single_config_log_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("MONITOR_REFRESH_SECONDS", "20")
    config = make_bot_config(
        symbols=("SPY",),
        decision_log_path=str(tmp_path / "decisions.csv"),
        fill_log_path=str(tmp_path / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "snapshot.csv"),
    )

    monitor_config = load_monitor_configuration(config=config)

    assert monitor_config.refresh_seconds == 20
    assert monitor_config.read_only is True
    assert len(monitor_config.instances) == 1
    assert monitor_config.instances[0].decision_log_path == Path(config.decision_log_path)


def test_sanitize_symbol_for_path_removes_non_alphanumeric_characters():
    assert sanitize_symbol_for_path("BTC/USD") == "btcusd"
    assert sanitize_symbol_for_path("ETH-USDC") == "ethusdc"


def test_monitor_fixture_builder_supports_phase_two_states(tmp_path):
    for state in (
        "healthy",
        "no_data",
        "malformed",
        "stale",
        "blocked_live",
        "failed",
        "broker_rejection",
        "archived_failed",
        "mixed_current_historical",
        "no_recent_fill",
    ):
        paths = create_monitor_fixture(tmp_path / state, state, symbol="BTC/USD")

        assert set(paths) == {"decisions", "fills", "snapshot"}
        assert paths["decisions"].name == "decisions.csv"


def test_filter_active_evidence_keeps_only_rows_inside_active_window():
    frame = pd.DataFrame(
        [
            {"timestamp": "2026-04-25T10:00:00+00:00", "symbol": "BTC/USD"},
            {"timestamp": "2026-04-25T13:00:00+00:00", "symbol": "BTC/USD"},
        ]
    )

    filtered = _filter_active_evidence(
        frame,
        reference=datetime(2026, 4, 25, 13, 30, tzinfo=timezone.utc),
        active_minutes=60,
    )

    assert list(filtered["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")) == ["2026-04-25T13:00:00+0000"]


def test_select_authoritative_account_instance_prefers_freshest_current_snapshot(tmp_path):
    old_paths = create_monitor_fixture(tmp_path / "old", "healthy", symbol="BTC/USD")
    fresh_paths = create_monitor_fixture(tmp_path / "fresh", "healthy", symbol="ETH/USD")
    old_summary = summarize_instance(
        DashboardInstance(
            label="BTC/USD",
            symbols=("BTC/USD",),
            asset_classes=("crypto",),
            decision_log_path=old_paths["decisions"],
            fill_log_path=old_paths["fills"],
            snapshot_log_path=old_paths["snapshot"],
        )
    )
    fresh_summary = summarize_instance(
        DashboardInstance(
            label="ETH/USD",
            symbols=("ETH/USD",),
            asset_classes=("crypto",),
            decision_log_path=fresh_paths["decisions"],
            fill_log_path=fresh_paths["fills"],
            snapshot_log_path=fresh_paths["snapshot"],
        )
    )
    old_snapshot = Path(old_paths["snapshot"])
    old_snapshot.write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                "2026-04-25T09:00:00+00:00,live,BTC/USD,100.0,90.0,0.1,0.0",
            ]
        ),
        encoding="utf-8",
    )
    fresh_snapshot = Path(fresh_paths["snapshot"])
    fresh_snapshot.write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                "2026-04-25T13:20:00+00:00,live,ETH/USD,101.0,80.0,0.2,1.0",
            ]
        ),
        encoding="utf-8",
    )
    old_summary = summarize_instance(old_summary)
    fresh_summary = summarize_instance(fresh_summary)

    selected = _select_authoritative_account_instance(
        [old_summary, fresh_summary],
        reference=datetime(2026, 4, 25, 13, 30, tzinfo=timezone.utc),
        stale_after_minutes=180,
    )

    assert selected is not None
    assert selected.label == "ETH/USD"


def test_value_evidence_falls_back_to_snapshot_delta_when_recent_fill_missing():
    unit_value, held_value, source = _value_evidence(
        SnapshotSummary(
            timestamp="2026-04-25T13:20:00+00:00",
            mode="live",
            symbol="BTC/USD",
            portfolio_value="100.0",
            cash="80.0",
            position_qty="2.0",
            day_pnl="0.5",
        ),
        None,
    )

    assert unit_value == 10.0
    assert held_value == 20.0
    assert source == VALUE_SOURCE_SNAPSHOT_DELTA


def test_dashboard_status_uses_snapshot_delta_held_value_without_recent_fill(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "no_recent_fill", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["held_value_source"] == VALUE_SOURCE_SNAPSHOT_DELTA
    assert item["held_value"] == 20.0
    assert item["held_value_estimate"] == 20.0
    assert item["latest_fill_price"] == 10.0


def test_dashboard_status_uses_provisional_fill_state_when_fill_is_newer_than_snapshot(tmp_path):
    paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    Path(paths["snapshot"]).write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                "2026-04-30T17:45:00+00:00,live,ETH/USD,99.10,59.91,0.0,0.0",
            ]
        ),
        encoding="utf-8",
    )
    Path(paths["fills"]).write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,side,quantity,order_id,portfolio_value,cash,notional_usd,result",
                "2026-04-30T17:45:16+00:00,live,ETH/USD,crypto,buy,0.00702909,order-1,99.10,63.414264,15.855736,filled",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
        runtime_state="running",
        runtime_mode_context="live",
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["position_qty"] == 0.00702909
    assert item["cash"] == 63.414264
    assert item["held_value_source"] == VALUE_SOURCE_FILL_DELTA
    assert item["portfolio_is_provisional"] is True
    assert item["freshness_state"] == "provisional"
    assert "fresher fill evidence" in item["freshness_explanation"]


def test_dashboard_status_exposes_symbol_scoped_warning_events(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "broker_rejection", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["active_warnings"]
    assert item["active_warnings"][0]["symbol"] == "BTC/USD"
    assert item["active_warnings"][0]["warning_type"] == "broker_rejection"


def test_dashboard_status_exposes_symbol_scoped_runtime_event_summary(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
        runtime_state="running",
        runtime_mode_context="live",
        runtime_status_message="Runtime is running.",
        runtime_session_id="session-btc",
        runtime_last_seen_utc="2026-04-30T00:46:00+00:00",
        last_lifecycle_event="running",
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert any(event["symbol"] == "BTC/USD" for event in item["recent_runtime_events"])
    assert any(event["runtime_session_id"] == "session-btc" for event in item["recent_runtime_events"])
    assert any(event["event_source"] == "runtime_manager" for event in item["recent_runtime_events"])


def test_dashboard_status_prefers_live_badge_for_running_managed_stock_runtime_without_trade_rows(tmp_path):
    paths = create_monitor_fixture(tmp_path / "spy", "no_data", symbol="SPY")
    Path(paths["decisions"]).write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,quantity,portfolio_value,cash,reason,result",
                "2026-04-30T17:43:51+00:00,active-live,SYSTEM,system,hold,guardrail,,,,,0,,,runtime started,started",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="SPY",
        symbols=("SPY",),
        asset_classes=("stock",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
        runtime_state="running",
        runtime_mode_context="live",
    )

    summary = summarize_instance(instance)
    payload = dashboard_status((summary,))
    item = payload["instances"][0]

    assert summary.status.state == "live"
    assert item["status_state"] == "live"
    assert item["latest_mode"] == "live"


def test_dashboard_status_prefers_current_healthy_restart_over_old_failed_evidence(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "mixed_current_historical", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["status"]["state"] == "live"
    assert item["latest_reason"] == "delta_qty_zero"
    assert not any(issue["category"] == "failed" for issue in item["issues"])
    assert item["historical_issue_count"] == 1
    assert payload["historical_context"]["historical_issue_count"] == 1


def test_dashboard_status_bounds_historical_issue_reporting(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "mixed_current_historical", symbol="BTC/USD")
    now = datetime.now(timezone.utc)
    Path(paths["decisions"]).write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,quantity,portfolio_value,cash,reason,result",
                f"{(now - pd.Timedelta(hours=4)).isoformat()},active-live,SYSTEM,system,hold,guardrail,,,,,0,,,old failed one,failed",
                f"{(now - pd.Timedelta(hours=3, minutes=30)).isoformat()},active-live,SYSTEM,system,hold,guardrail,,,,,0,,,old failed two,failed",
                f"{(now - pd.Timedelta(hours=3, minutes=10)).isoformat()},active-live,SYSTEM,system,hold,guardrail,,,,,0,,,old failed three,failed",
                f"{(now - pd.Timedelta(minutes=5)).isoformat()},live,BTC/USD,crypto,hold,model,0.65,external,1.0,neutral,0,100.0,90.0,delta_qty_zero,skipped",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,), historical_issue_limit=2)

    assert payload["aggregate_state"] == "live"
    assert payload["historical_context"]["historical_issue_count"] == 2
    assert len(payload["historical_context"]["historical_issues"]) == 2


def test_dashboard_status_ignores_archived_instance_for_current_aggregate_state(tmp_path):
    current_paths = create_monitor_fixture(tmp_path / "current", "healthy", symbol="BTC/USD")
    archived_paths = create_monitor_fixture(tmp_path / "history", "archived_failed", symbol="ETH/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=current_paths["decisions"],
                fill_log_path=current_paths["fills"],
                snapshot_log_path=current_paths["snapshot"],
            ),
            DashboardInstance(
                label="ETH/USD-old",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=archived_paths["decisions"],
                fill_log_path=archived_paths["fills"],
                snapshot_log_path=archived_paths["snapshot"],
            ),
        )
    )

    assert payload["aggregate_state"] in {"paper", "running"}
    assert len(payload["instances"]) == 1
    assert payload["instances"][0]["label"] == "BTC/USD"
    assert payload["historical_context"]["historical_instance_count"] == 1
    assert payload["historical_context"]["historical_issue_count"] >= 1


def test_dashboard_status_separates_negative_pnl_into_notes_not_issues(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "no_recent_fill", symbol="BTC/USD")
    now = datetime.now(timezone.utc)
    Path(paths["snapshot"]).write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                f"{now.isoformat()},live,BTC/USD,99.0,80.0,2.0,-0.5",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert any(note["category"] == "negative_pnl" for note in payload["notes"])
    assert any(note["category"] == "negative_pnl" for note in item["notes"])
    assert not any(issue["category"] == "negative_pnl" for issue in payload["issues"])


def test_dashboard_status_includes_last_activity_times_and_broker_rejection_count(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "broker_rejection", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["last_decision_utc"]
    assert item["last_fill_utc"] == ""
    assert item["broker_rejection_count"] == 1


def test_dashboard_status_aggregates_at_least_ten_instances(tmp_path):
    instances = []
    for index in range(10):
        symbol = f"SYM{index}"
        paths = create_monitor_fixture(tmp_path / symbol, "healthy", symbol=symbol)
        instances.append(
            DashboardInstance(
                label=symbol,
                symbols=(symbol,),
                asset_classes=("stock",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
            )
        )

    payload = dashboard_status(tuple(instances))

    assert payload["aggregate_state"] in {"paper", "running"}
    assert len(payload["instances"]) == 10
    assert all(item["latest_reason"] for item in payload["instances"])


def test_fixture_states_map_to_distinct_dashboard_statuses(tmp_path):
    expected = {
        "blocked_live": "blocked",
        "stale": "stale",
        "failed": "failed",
        "malformed": "no_data",
        "broker_rejection": "live",
        "no_data": "no_data",
    }

    for state, expected_status in expected.items():
        paths = create_monitor_fixture(tmp_path / state, state, symbol="BTC/USD")
        instance = DashboardInstance(
            label=state,
            symbols=("BTC/USD",),
            asset_classes=("crypto",),
            decision_log_path=paths["decisions"],
            fill_log_path=paths["fills"],
            snapshot_log_path=paths["snapshot"],
        )

        summary = summarize_instance(instance)

        assert summary.status.state == expected_status
        assert summary.issues or expected_status == "no_data"


def test_dashboard_status_includes_recent_issue_summaries_for_problem_states(tmp_path):
    problem_states = ("blocked_live", "stale", "failed", "malformed", "broker_rejection")
    instances = []
    for state in problem_states:
        paths = create_monitor_fixture(tmp_path / state, state, symbol="BTC/USD")
        instances.append(
            DashboardInstance(
                label=state,
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
            )
        )

    payload = dashboard_status(tuple(instances))
    categories = {issue["category"] for issue in payload["issues"]}

    assert payload["aggregate_state"] == "failed"
    assert {"blocked", "stale_data", "failed", "malformed_csv", "broker_rejection"} <= categories


def test_broker_rejection_keeps_live_instance_visible_as_live_with_warning(tmp_path):
    paths = create_monitor_fixture(tmp_path / "broker_rejection", "broker_rejection", symbol="BTC/USD")
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    summary = summarize_instance(instance)

    assert summary.status.state == "live"
    assert summary.status.severity == "warning"
    assert any(issue.category == "broker_rejection" for issue in summary.issues)


def test_dashboard_status_includes_cross_instance_recent_activity(tmp_path):
    btc_paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    eth_paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=btc_paths["decisions"],
                fill_log_path=btc_paths["fills"],
                snapshot_log_path=btc_paths["snapshot"],
            ),
            DashboardInstance(
                label="ETH/USD",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=eth_paths["decisions"],
                fill_log_path=eth_paths["fills"],
                snapshot_log_path=eth_paths["snapshot"],
            ),
        )
    )

    assert payload["recent_activity_columns"][1] == "instance_label"
    labels = {row["instance_label"] for row in payload["recent_activity_rows"]}
    assert {"BTC/USD", "ETH/USD"} <= labels


def test_dashboard_status_includes_account_overview_from_freshest_instance(tmp_path):
    btc_paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    eth_paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    now = datetime.now(timezone.utc)
    btc_decisions = Path(btc_paths["decisions"])
    eth_decisions = Path(eth_paths["decisions"])
    btc_decisions.write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,quantity,portfolio_value,cash,reason,result",
                f"{(now - pd.Timedelta(minutes=10)).isoformat()},live,BTC/USD,crypto,hold,model,0.60,external,1.0,neutral,0,100.0,90.0,no_signal,skipped",
            ]
        ),
        encoding="utf-8",
    )
    eth_decisions.write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,quantity,portfolio_value,cash,reason,result",
                f"{(now - pd.Timedelta(minutes=5)).isoformat()},live,ETH/USD,crypto,buy,model,0.70,external,1.0,neutral,0.004,101.5,88.0,submitted,submitted",
            ]
        ),
        encoding="utf-8",
    )

    Path(btc_paths["snapshot"]).write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                f"{(now - pd.Timedelta(minutes=10)).isoformat()},live,BTC/USD,100.0,90.0,0.1,0.0",
            ]
        ),
        encoding="utf-8",
    )
    Path(eth_paths["snapshot"]).write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                f"{(now - pd.Timedelta(minutes=5)).isoformat()},live,ETH/USD,100.0,100.0,0.0,0.0",
            ]
        ),
        encoding="utf-8",
    )

    payload = dashboard_status(
        (
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=btc_paths["decisions"],
                fill_log_path=btc_paths["fills"],
                snapshot_log_path=btc_paths["snapshot"],
            ),
            DashboardInstance(
                label="ETH/USD",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=eth_paths["decisions"],
                fill_log_path=eth_paths["fills"],
                snapshot_log_path=eth_paths["snapshot"],
            ),
        )
    )

    assert payload["account_overview"]["source_instance"] == "ETH/USD"
    assert payload["account_overview"]["account_equity"] == 100.0
    assert payload["account_overview"]["cash"] == 100.0
    assert payload["account_overview"]["instances_count"] == 2
    assert payload["account_overview"]["is_stale"] is False


def test_monitor_reads_snapshot_rows_with_iso_timestamps(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    snapshot_path = paths["snapshot"]
    snapshot_path.write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                "2026-04-25T17:00:00+00:00,live,BTC/USD,100.00,90.00,0.0001,0.00",
                "2026-04-25T17:05:00+00:00,live,BTC/USD,101.50,88.00,0.0002,1.50",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="BTC/USD",
        symbols=("BTC/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=snapshot_path,
    )

    payload = dashboard_status((instance,))

    assert payload["instances"][0]["portfolio_value"] == 101.5
    assert payload["instances"][0]["day_pnl"] == 1.5


def test_monitor_reports_estimated_held_value_from_position_and_fill(tmp_path):
    paths = create_monitor_fixture(tmp_path / "eth", "healthy", symbol="ETH/USD")
    Path(paths["fills"]).write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,side,quantity,order_id,portfolio_value,cash,notional_usd,result",
                "2026-04-25T17:10:00+00:00,live,ETH/USD,crypto,buy,0.5,order-1,100.0,80.0,1000.0,submitted",
            ]
        ),
        encoding="utf-8",
    )
    Path(paths["snapshot"]).write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                "2026-04-25T17:15:00+00:00,live,ETH/USD,102.0,79.0,0.25,2.0",
            ]
        ),
        encoding="utf-8",
    )
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )

    payload = dashboard_status((instance,))
    item = payload["instances"][0]

    assert item["latest_fill_price"] == 2000.0
    assert item["held_value_estimate"] == 500.0
