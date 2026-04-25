from __future__ import annotations

from pathlib import Path

import pandas as pd

from tests.conftest import make_bot_config
from tests.fixtures.monitor.build_fixtures import create_monitor_fixture, recent_decision, write_decisions, write_malformed_csv
from tradingbot.app.monitor import (
    DashboardInstance,
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


def test_numeric_helpers_use_defaults_for_bad_values():
    assert to_float("12.5") == 12.5
    assert to_float("nope", default=7.0) == 7.0
    assert to_int("3") == 3
    assert to_int("nope", default=9) == 9


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
    for state in ("healthy", "no_data", "malformed", "stale", "blocked_live", "failed", "broker_rejection"):
        paths = create_monitor_fixture(tmp_path / state, state, symbol="BTC/USD")

        assert set(paths) == {"decisions", "fills", "snapshot"}
        assert paths["decisions"].name == "decisions.csv"


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
        "broker_rejection": "warning",
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
