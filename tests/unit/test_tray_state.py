from __future__ import annotations

from tradingbot.app.monitor import MonitorConfiguration
from tradingbot.app.tray import (
    TRAY_MENU_ACTIONS,
    TrayDependencies,
    create_tray_controller,
    tray_state_from_dashboard,
)


def test_tray_state_mapping_uses_dashboard_aggregate_state():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "live",
        "instances": [{"label": "BTC/USD"}, {"label": "SPY"}],
        "issues": [],
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "live"
    assert state.label.endswith("(Live)")
    assert "Instances: 2" in state.tooltip
    assert state.menu_actions == TRAY_MENU_ACTIONS


def test_tray_state_mapping_handles_warning_states():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "stale",
        "instances": [{"label": "BTC/USD"}],
        "issues": [{"severity": "warning"}],
        "notes": [],
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "stale"
    assert state.label.endswith("(Stale)")
    assert "Warnings: 1" in state.tooltip


def test_tray_state_mapping_highlights_critical_issue_aggregation():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "failed",
        "instances": [{"label": "BTC/USD"}, {"label": "ETH/USD"}],
        "issues": [{"severity": "critical"}, {"severity": "warning"}, {"severity": "critical"}],
        "notes": [],
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "failed"
    assert "Critical: 2" in state.tooltip
    assert "Warnings: 1" in state.tooltip


def test_tray_actions_only_use_monitor_callbacks():
    opened_urls: list[str] = []
    payload_calls: list[str] = []

    def payload_loader():
        payload_calls.append("refresh")
        return {
            "status_updated_utc": "2026-04-19 12:00:00 UTC",
            "aggregate_state": "paper",
            "instances": [{"label": "SPY"}],
            "issues": [],
            "notes": [],
        }

    def browser_opener(url: str):
        opened_urls.append(url)
        return True

    config = MonitorConfiguration(dashboard_host="127.0.0.1", dashboard_port=8080, instances=())
    controller = create_tray_controller(
        config=config,
        payload_loader=payload_loader,
        browser_opener=browser_opener,
        dependencies=TrayDependencies(available=False, reason="pystray missing"),
    )

    menu = {item["label"]: item["callback"] for item in controller.build_menu_model()}
    menu["Refresh Status"]()
    menu["Open Dashboard"]()
    menu["Exit Monitor"]()

    assert payload_calls == ["refresh"]
    assert opened_urls == ["http://127.0.0.1:8080/"]
    assert controller.exit_requested is True


def test_tray_state_mapping_counts_notes_without_escalating_severity():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "live",
        "instances": [{"label": "BTC/USD"}],
        "issues": [],
        "notes": [{"category": "negative_pnl"}],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "live"
    assert "Issues: 0." in state.tooltip
    assert "Notes: 1." in state.tooltip


def test_tray_state_mapping_reports_historical_context_without_escalating_state():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "live",
        "instances": [{"label": "BTC/USD"}],
        "issues": [],
        "notes": [],
        "historical_context": {"historical_issue_count": 2},
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "live"
    assert "Historical: 2." in state.tooltip


def test_tray_state_mapping_reports_running_and_failed_runtime_counts():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "live",
        "instances": [
            {"label": "BTC/USD", "runtime_state": "running", "runtime_last_seen_utc": "2026-04-19T12:00:00+00:00"},
            {"label": "ETH/USD", "runtime_state": "failed", "runtime_last_seen_utc": "2026-04-19T11:59:00+00:00"},
            {"label": "SOL/USD", "runtime_state": "stopped", "runtime_last_seen_utc": ""},
        ],
        "issues": [],
        "notes": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Running runtimes: 1." in state.tooltip
    assert "Failed runtimes: 1." in state.tooltip
    assert "Runtime refresh: 2026-04-19T12:00:00+00:00." in state.tooltip


def test_tray_state_mapping_handles_stopped_runtime_aggregate_state():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "stopped",
        "instances": [{"label": "BTC/USD", "runtime_state": "stopped", "runtime_last_seen_utc": "2026-04-19T11:59:00+00:00"}],
        "issues": [],
        "notes": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "stopped"
    assert state.label.endswith("(Stopped)")
    assert "Running runtimes: 0." in state.tooltip


def test_tray_state_mapping_includes_latest_control_outcome_summary():
    payload = {
        "status_updated_utc": "2026-04-19 12:00:00 UTC",
        "aggregate_state": "live",
        "instances": [
            {"label": "BTC/USD", "runtime_state": "running", "runtime_last_seen_utc": "2026-04-19T12:00:00+00:00", "control_mode_context": "live"},
            {"label": "SPY", "runtime_state": "stopped", "runtime_last_seen_utc": "2026-04-19T11:59:00+00:00", "control_mode_context": "paper"},
        ],
        "issues": [],
        "notes": [],
        "recent_control_actions": [
            {
                "requested_action": "restart",
                "symbol": "BTC/USD",
                "asset_class": "crypto",
                "outcome_state": "succeeded",
            }
        ],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Latest control: restart BTC/USD (crypto) succeeded." in state.tooltip
    assert "Live controls: 1." in state.tooltip
    assert "Paper controls: 1." in state.tooltip


def test_tray_state_mapping_reports_reconciled_runtime_counts_even_without_issue_rows():
    payload = {
        "status_updated_utc": "2026-04-30 00:46:00 UTC",
        "aggregate_state": "live",
        "instances": [
            {"label": "BTC/USD", "runtime_state": "running", "runtime_last_seen_utc": "2026-04-30T00:46:00+00:00"},
            {"label": "ETH/USD", "runtime_state": "failed", "runtime_last_seen_utc": "2026-04-30T00:45:30+00:00"},
        ],
        "issues": [],
        "notes": [],
        "recent_control_actions": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Running runtimes: 1." in state.tooltip
    assert "Failed runtimes: 1." in state.tooltip


def test_tray_state_mapping_uses_runtime_mode_context_when_control_mode_context_is_missing():
    payload = {
        "status_updated_utc": "2026-04-30 00:46:00 UTC",
        "aggregate_state": "live",
        "instances": [
            {"label": "BTC/USD", "runtime_state": "running", "runtime_last_seen_utc": "2026-04-30T00:46:00+00:00", "runtime_mode_context": "live"},
            {"label": "SPY", "runtime_state": "stopped", "runtime_last_seen_utc": "2026-04-30T00:45:30+00:00", "runtime_mode_context": "paper"},
        ],
        "issues": [],
        "notes": [],
        "recent_control_actions": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Live controls: 1." in state.tooltip
    assert "Paper controls: 1." in state.tooltip


def test_tray_state_mapping_includes_latest_active_warning_summary():
    payload = {
        "status_updated_utc": "2026-04-30 00:46:00 UTC",
        "aggregate_state": "failed",
        "instances": [
            {
                "label": "BTC/USD",
                "runtime_state": "failed",
                "runtime_last_seen_utc": "2026-04-30T00:46:00+00:00",
                "runtime_mode_context": "live",
                "active_warnings": [
                    {
                        "warning_type": "runtime_failed",
                        "symbol": "BTC/USD",
                        "timestamp_utc": "2026-04-30T00:46:00+00:00",
                    }
                ],
            }
        ],
        "issues": [{"severity": "critical"}],
        "notes": [],
        "recent_control_actions": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Latest warning: runtime_failed BTC/USD." in state.tooltip


def test_tray_state_mapping_reports_portfolio_freshness_semantics():
    payload = {
        "status_updated_utc": "2026-04-30 00:46:00 UTC",
        "aggregate_state": "live",
        "instances": [
            {"label": "BTC/USD", "runtime_state": "running", "freshness_state": "current"},
            {"label": "ETH/USD", "runtime_state": "running", "freshness_state": "provisional"},
            {"label": "SPY", "runtime_state": "stopped", "freshness_state": "historical"},
        ],
        "issues": [],
        "notes": [],
        "recent_control_actions": [],
        "historical_context": {"historical_issue_count": 0},
    }

    state = tray_state_from_dashboard(payload)

    assert "Portfolio freshness - provisional: 1, stale: 0, unavailable: 0, historical: 1." in state.tooltip
