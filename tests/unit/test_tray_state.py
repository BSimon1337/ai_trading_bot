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
    }

    state = tray_state_from_dashboard(payload)

    assert state.state == "stale"
    assert state.label.endswith("(Stale)")
    assert "Issues: 1" in state.tooltip


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
