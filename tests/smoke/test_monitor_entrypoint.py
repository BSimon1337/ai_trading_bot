from __future__ import annotations

import monitor_app
from tests.fixtures.monitor.build_fixtures import create_monitor_fixture
from tradingbot.app.monitor import DashboardInstance
from tradingbot.app.monitor import MonitorConfiguration
from tradingbot.app import tray as tray_module


def test_monitor_app_root_entrypoint_exposes_app():
    assert monitor_app.APP is not None
    assert monitor_app.APP.test_client().get("/health").status_code == 200


def test_monitor_dashboard_renders_no_data_state():
    client = monitor_app.create_app(instances=()).test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Trading Bot Monitor" in response.data
    assert b"No monitored instances" in response.data


def test_tray_module_no_tray_entrypoint_starts_dashboard(monkeypatch):
    calls: dict[str, object] = {}

    class FakeApp:
        def run(self, **kwargs):
            calls["run_kwargs"] = kwargs

    def fake_app_factory(*, instances, refresh_seconds):
        calls["instances"] = instances
        calls["refresh_seconds"] = refresh_seconds
        return FakeApp()

    exit_code = tray_module.run_monitor(
        argv=["--no-tray", "--host", "127.0.0.1", "--port", "8091", "--refresh-seconds", "5"],
        config=MonitorConfiguration(instances=()),
        app_factory=fake_app_factory,
    )

    assert exit_code == 0
    assert calls["instances"] == ()
    assert calls["refresh_seconds"] == 5
    assert calls["run_kwargs"] == {
        "host": "127.0.0.1",
        "port": 8091,
        "debug": False,
        "use_reloader": False,
    }


def test_monitor_app_root_main_uses_monitor_configuration(monkeypatch):
    calls: dict[str, object] = {}

    class FakeApp:
        def run(self, **kwargs):
            calls["run_kwargs"] = kwargs

    def fake_create_app(*, instances, refresh_seconds):
        calls["instances"] = instances
        calls["refresh_seconds"] = refresh_seconds
        return FakeApp()

    config = MonitorConfiguration(dashboard_host="127.0.0.1", dashboard_port=8092, instances=())
    monkeypatch.setattr(monitor_app, "load_monitor_configuration", lambda: config)
    monkeypatch.setattr(monitor_app, "create_app", fake_create_app)

    exit_code = monitor_app.main()

    assert exit_code == 0
    assert calls["instances"] == ()
    assert calls["refresh_seconds"] == config.refresh_seconds
    assert calls["run_kwargs"] == {
        "host": "127.0.0.1",
        "port": 8092,
        "debug": False,
        "use_reloader": False,
    }


def test_monitor_app_handles_current_and_archived_evidence_without_polluting_live_state(tmp_path):
    current_paths = create_monitor_fixture(tmp_path / "current", "healthy", symbol="BTC/USD")
    archived_paths = create_monitor_fixture(tmp_path / "history", "archived_failed", symbol="ETH/USD")
    client = monitor_app.create_app(
        instances=(
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
    ).test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert payload["aggregate_state"] in {"paper", "running"}
    assert len(payload["instances"]) == 1
    assert payload["historical_context"]["historical_instance_count"] == 1
    assert "Historical Context" in page_text
