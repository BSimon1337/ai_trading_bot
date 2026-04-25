from __future__ import annotations

from tradingbot.app.monitor import MonitorConfiguration
from tradingbot.app.tray import (
    TRAY_MENU_ACTIONS,
    TrayDependencies,
    create_tray_controller,
    start_monitor_tray,
)


class FakeMenuItem:
    def __init__(self, label, callback):
        self.label = label
        self.callback = callback


class FakeMenu(tuple):
    def __new__(cls, *items):
        return super().__new__(cls, items)


class FakeIcon:
    def __init__(self, name, image, title, menu):
        self.name = name
        self.icon = image
        self.title = title
        self.menu = menu
        self.ran_detached = False
        self.stopped = False

    def run_detached(self):
        self.ran_detached = True

    def stop(self):
        self.stopped = True


class FakePystray:
    MenuItem = FakeMenuItem
    Menu = FakeMenu
    Icon = FakeIcon


class FakeImage:
    @staticmethod
    def new(mode, size, color):
        return {"mode": mode, "size": size, "color": color}


class FakeDrawHandle:
    def __init__(self, image):
        self.image = image
        self.operations: list[tuple[str, object]] = []

    def rounded_rectangle(self, bounds, radius, fill):
        self.operations.append(("rounded_rectangle", bounds, radius, fill))

    def ellipse(self, bounds, fill):
        self.operations.append(("ellipse", bounds, fill))


class FakeImageDraw:
    @staticmethod
    def Draw(image):
        return FakeDrawHandle(image)


def test_tray_monitor_contract_starts_with_expected_menu_and_state():
    controller, result = start_monitor_tray(
        config=MonitorConfiguration(dashboard_host="127.0.0.1", dashboard_port=8080, instances=()),
        payload_loader=lambda: {
            "status_updated_utc": "2026-04-19 12:00:00 UTC",
            "aggregate_state": "paper",
            "instances": [{"label": "SPY"}],
            "issues": [],
            "notes": [],
        },
        browser_opener=lambda url: True,
        dependencies=TrayDependencies(
            available=True,
            pystray=FakePystray,
            image_module=FakeImage,
            image_draw_module=FakeImageDraw,
        ),
    )

    assert result["mode"] == "tray"
    assert result["state"] == "paper"
    assert controller.state.menu_actions == TRAY_MENU_ACTIONS
    assert controller.icon is not None
    assert controller.icon.ran_detached is True
    assert [item.label for item in controller.icon.menu] == list(TRAY_MENU_ACTIONS)


def test_tray_monitor_contract_supports_degraded_mode_without_pystray():
    controller = create_tray_controller(
        config=MonitorConfiguration(instances=()),
        payload_loader=lambda: {
            "status_updated_utc": "2026-04-19 12:00:00 UTC",
            "aggregate_state": "no_data",
            "instances": [],
            "issues": [],
            "notes": [],
        },
        dependencies=TrayDependencies(available=False, reason="pystray unavailable"),
    )

    result = controller.start()

    assert result["mode"] == "degraded"
    assert result["reason"] == "pystray unavailable"
    assert result["state"] == "no_data"
    assert controller.icon is None


def test_tray_monitor_contract_keeps_notes_out_of_warning_state():
    controller, result = start_monitor_tray(
        config=MonitorConfiguration(dashboard_host="127.0.0.1", dashboard_port=8080, instances=()),
        payload_loader=lambda: {
            "status_updated_utc": "2026-04-19 12:00:00 UTC",
            "aggregate_state": "live",
            "instances": [{"label": "BTC/USD"}],
            "issues": [],
            "notes": [{"category": "negative_pnl", "symbol": "BTC/USD"}],
        },
        browser_opener=lambda url: True,
        dependencies=TrayDependencies(
            available=True,
            pystray=FakePystray,
            image_module=FakeImage,
            image_draw_module=FakeImageDraw,
        ),
    )

    assert result["state"] == "live"
    assert "Notes: 1." in controller.state.tooltip
    assert "Warnings: 0." not in controller.state.tooltip


def test_tray_monitor_contract_shows_historical_context_without_changing_live_state():
    controller, result = start_monitor_tray(
        config=MonitorConfiguration(dashboard_host="127.0.0.1", dashboard_port=8080, instances=()),
        payload_loader=lambda: {
            "status_updated_utc": "2026-04-19 12:00:00 UTC",
            "aggregate_state": "live",
            "instances": [{"label": "BTC/USD"}],
            "issues": [],
            "notes": [],
            "historical_context": {"historical_issue_count": 3},
        },
        browser_opener=lambda url: True,
        dependencies=TrayDependencies(
            available=True,
            pystray=FakePystray,
            image_module=FakeImage,
            image_draw_module=FakeImageDraw,
        ),
    )

    assert result["state"] == "live"
    assert "Historical: 3." in controller.state.tooltip
