from __future__ import annotations

import monitor_app
from tests.fixtures.monitor.build_fixtures import create_monitor_fixture
from tradingbot.app.monitor import DashboardInstance
from tradingbot.app.monitor import MonitorConfiguration
from tradingbot.app import tray as tray_module
from tests.conftest import make_bot_config


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


def test_monitor_app_renders_mixed_sentiment_fallback_and_stale_evidence(tmp_path):
    current_paths = create_monitor_fixture(tmp_path / "current", "healthy", symbol="BTC/USD")
    fallback_paths = create_monitor_fixture(tmp_path / "fallback", "healthy", symbol="ETH/USD")
    current_paths["decisions"].write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,sentiment_availability_state,sentiment_is_fallback,sentiment_observed_at,headline_count,headline_preview,sentiment_window_start,sentiment_window_end,quantity,portfolio_value,cash,reason,result",
                "2026-04-26T15:00:00+00:00,live,BTC/USD,crypto,hold,model,0.7,external,0.82,positive,news_scored,false,2026-04-26T10:00:00+00:00,3,\"[\"\"BTC gains on ETF chatter\"\",\"\"Volume rises\"\",\"\"Risk appetite improves\"\"]\",2026-04-23,2026-04-26,0,100,90,hold,skipped",
            ]
        ),
        encoding="utf-8",
    )
    fallback_paths["decisions"].write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,sentiment_availability_state,sentiment_is_fallback,sentiment_observed_at,headline_count,headline_preview,sentiment_window_start,sentiment_window_end,quantity,portfolio_value,cash,reason,result",
                "2026-04-26T15:00:00+00:00,live,ETH/USD,crypto,hold,model,0.55,neutral_fallback,0.0,neutral,neutral_fallback,true,2026-04-26T15:00:00+00:00,0,[],2026-04-23,2026-04-26,0,100,90,hold,skipped",
            ]
        ),
        encoding="utf-8",
    )
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
                label="ETH/USD",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=fallback_paths["decisions"],
                fill_log_path=fallback_paths["fills"],
                snapshot_log_path=fallback_paths["snapshot"],
            ),
        )
    ).test_client()

    response = client.get("/")
    payload = client.get("/api/status").get_json()
    page_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Recent Headlines" in page_text
    assert "Sentiment Trend" in page_text
    assert any(item["sentiment_availability_state"] == "stale_news_scored" for item in payload["instances"])
    assert any(item["sentiment_is_fallback"] is True for item in payload["instances"])


def test_monitor_dashboard_control_routes_accept_post_actions(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    config = make_bot_config(symbols=("BTC/USD",))
    calls: list[tuple[str, str, str]] = []

    def fake_start_action(config, symbol, **kwargs):
        del config
        calls.append(("start", symbol, kwargs.get("mode", "")))
        return {
            "action_id": "start-1",
            "symbol": symbol,
            "asset_class": "crypto",
            "requested_action": "start",
            "mode_context": "live",
            "requested_at_utc": "2026-04-28T02:00:00+00:00",
            "requested_from": "dashboard",
            "confirmation_state": "not_required",
            "outcome_state": "succeeded",
            "outcome_message": "Runtime is running.",
            "runtime_session_id": "session-btc",
        }

    def fake_stop_action(config, symbol, **kwargs):
        del config, kwargs
        calls.append(("stop", symbol, ""))
        return {
            "action_id": "stop-1",
            "symbol": symbol,
            "asset_class": "crypto",
            "requested_action": "stop",
            "mode_context": "live",
            "requested_at_utc": "2026-04-28T02:01:00+00:00",
            "requested_from": "dashboard",
            "confirmation_state": "not_required",
            "outcome_state": "succeeded",
            "outcome_message": "Runtime stopped by operator.",
            "runtime_session_id": "session-btc",
        }

    def fake_restart_action(config, symbol, **kwargs):
        del config
        calls.append(("restart", symbol, kwargs.get("mode", "")))
        return {
            "action_id": "restart-1",
            "symbol": symbol,
            "asset_class": "crypto",
            "requested_action": "restart",
            "mode_context": "live",
            "requested_at_utc": "2026-04-28T02:02:00+00:00",
            "requested_from": "dashboard",
            "confirmation_state": "not_required",
            "outcome_state": "succeeded",
            "outcome_message": "Runtime is running.",
            "runtime_session_id": "session-btc-2",
        }

    client = monitor_app.create_app(
        instances=(
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=paths["decisions"],
                fill_log_path=paths["fills"],
                snapshot_log_path=paths["snapshot"],
                runtime_state="running",
                runtime_mode_context="live",
            ),
        ),
        config=config,
        start_action_runner=fake_start_action,
        stop_action_runner=fake_stop_action,
        restart_action_runner=fake_restart_action,
    ).test_client()

    assert client.post("/control/start", data={"symbol": "BTC/USD", "mode_context": "live"}).status_code == 200
    assert client.post("/control/stop", data={"symbol": "BTC/USD"}).status_code == 200
    assert client.post("/control/restart", data={"symbol": "BTC/USD", "mode_context": "live"}).status_code == 200
    assert calls == [("start", "BTC/USD", "live"), ("stop", "BTC/USD", ""), ("restart", "BTC/USD", "live")]
