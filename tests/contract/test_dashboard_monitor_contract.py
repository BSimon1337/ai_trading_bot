from __future__ import annotations

from tests.fixtures.monitor.build_fixtures import create_monitor_fixture
from tradingbot.app.monitor import DashboardInstance, create_app


def _instance(root, label: str = "BTC/USD") -> DashboardInstance:
    paths = create_monitor_fixture(root, "healthy", symbol=label)
    return DashboardInstance(
        label=label,
        symbols=(label,),
        asset_classes=("crypto",),
        decision_log_path=paths["decisions"],
        fill_log_path=paths["fills"],
        snapshot_log_path=paths["snapshot"],
    )


def test_dashboard_routes_expose_required_contract_fields(tmp_path):
    app = create_app(instances=(_instance(tmp_path / "btc"),))
    client = app.test_client()

    status_response = client.get("/api/status")
    health_response = client.get("/health")
    page_response = client.get("/")

    assert status_response.status_code == 200
    payload = status_response.get_json()
    assert set(payload) >= {"status_updated_utc", "aggregate_state", "instances", "issues", "recent_activity_columns", "recent_activity_rows"}
    assert payload["instances"][0]["label"] == "BTC/USD"
    assert set(payload["instances"][0]) >= {
        "status",
        "symbols",
        "latest_action",
        "latest_reason",
        "latest_mode",
        "latest_asset_class",
        "latest_update_utc",
        "heartbeat_age_minutes",
        "decisions_today",
        "fills_today",
        "recent_decisions",
        "recent_fills",
        "issues",
    }
    assert health_response.status_code == 200
    assert health_response.get_json()["ok"] is True
    assert page_response.status_code == 200
    assert b"Trading Bot Monitor" in page_response.data
    assert b"Recent Decisions Across Monitored Instances" in page_response.data


def test_dashboard_contract_handles_missing_evidence_without_crashing(tmp_path):
    instance = DashboardInstance(
        label="ETH/USD",
        symbols=("ETH/USD",),
        asset_classes=("crypto",),
        decision_log_path=tmp_path / "missing_decisions.csv",
        fill_log_path=tmp_path / "missing_fills.csv",
        snapshot_log_path=tmp_path / "missing_snapshot.csv",
    )
    app = create_app(instances=(instance,))
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page = client.get("/")

    assert payload["instances"][0]["status"]["state"] == "no_data"
    assert payload["instances"][0]["issues"]
    assert page.status_code == 200
    assert b"No runtime evidence" in page.data


def test_dashboard_contract_does_not_expose_secret_values(tmp_path, monkeypatch):
    monkeypatch.setenv("API_KEY", "do-not-show-this")
    monkeypatch.setenv("API_SECRET", "also-do-not-show-this")
    app = create_app(instances=(_instance(tmp_path / "btc"),))
    client = app.test_client()

    status_text = client.get("/api/status").get_data(as_text=True)
    page_text = client.get("/").get_data(as_text=True)

    assert "do-not-show-this" not in status_text
    assert "also-do-not-show-this" not in status_text
    assert "do-not-show-this" not in page_text
    assert "also-do-not-show-this" not in page_text


def test_dashboard_contract_renders_recent_issues_and_critical_states(tmp_path):
    blocked_paths = create_monitor_fixture(tmp_path / "blocked", "blocked_live", symbol="BTC/USD")
    malformed_paths = create_monitor_fixture(tmp_path / "malformed", "malformed", symbol="ETH/USD")
    app = create_app(
        instances=(
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=blocked_paths["decisions"],
                fill_log_path=blocked_paths["fills"],
                snapshot_log_path=blocked_paths["snapshot"],
            ),
            DashboardInstance(
                label="ETH/USD",
                symbols=("ETH/USD",),
                asset_classes=("crypto",),
                decision_log_path=malformed_paths["decisions"],
                fill_log_path=malformed_paths["fills"],
                snapshot_log_path=malformed_paths["snapshot"],
            ),
        )
    )
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert payload["aggregate_state"] in {"blocked", "failed"}
    assert any(issue["category"] == "blocked" for issue in payload["issues"])
    assert any(issue["category"] == "malformed_csv" for issue in payload["issues"])
    assert "Recent Issues" in page_text
    assert "blocked" in page_text
    assert "malformed_csv" in page_text
