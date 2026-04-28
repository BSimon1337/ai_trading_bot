from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.conftest import make_bot_config
from tests.fixtures.monitor.build_fixtures import create_monitor_fixture, write_runtime_registry
from tradingbot.app.monitor import DashboardInstance, create_app, load_monitor_configuration


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
    assert set(payload) >= {
        "status_updated_utc",
        "aggregate_state",
        "account_overview",
        "historical_context",
        "instances",
        "recent_control_actions",
        "latest_control_updated_at_utc",
        "issues",
        "notes",
        "recent_activity_columns",
        "recent_activity_rows",
    }
    assert set(payload["account_overview"]) >= {
        "cash",
        "account_equity",
        "day_pnl",
        "source_instance",
        "latest_update_utc",
        "instances_count",
        "instances_with_fills",
        "is_stale",
    }
    assert payload["instances"][0]["label"] == "BTC/USD"
    assert set(payload["instances"][0]) >= {
        "status",
        "symbols",
        "latest_action",
        "latest_reason",
        "latest_mode",
        "latest_asset_class",
        "latest_update_utc",
        "runtime_state",
        "runtime_status_message",
        "runtime_session_id",
        "runtime_pid",
        "runtime_started_at_utc",
        "runtime_last_seen_utc",
        "last_lifecycle_event",
        "is_fresh_runtime_session",
        "control_asset_class",
        "control_mode_context",
        "control_runtime_state",
        "can_start",
        "can_stop",
        "can_restart",
        "control_availability_message",
        "requires_live_confirmation",
        "last_decision_utc",
        "last_fill_utc",
        "broker_rejection_count",
        "evidence_scope",
        "historical_issue_count",
        "historical_issues",
        "heartbeat_age_minutes",
        "decisions_today",
        "fills_today",
        "recent_decisions",
        "recent_fills",
        "issues",
        "notes",
        "held_value",
        "held_value_source",
        "sentiment_label",
        "sentiment_probability",
        "sentiment_source",
        "sentiment_availability_state",
        "sentiment_is_fallback",
        "sentiment_last_updated_utc",
        "headline_count",
        "headline_preview",
        "sentiment_trend",
        "sentiment_headline_source_window",
    }
    assert health_response.status_code == 200
    assert health_response.get_json()["ok"] is True
    assert page_response.status_code == 200
    assert b"Trading Bot Monitor" in page_response.data
    assert b"Recent Decisions Across Monitored Instances" in page_response.data
    assert b"Sentiment State" in page_response.data
    assert b"Recent Headlines" in page_response.data
    assert b"Sentiment Trend" in page_response.data
    assert b"Runtime State" in page_response.data
    assert b"Start" in page_response.data
    assert b"Stop" in page_response.data
    assert b"Restart" in page_response.data


def test_dashboard_contract_exposes_runtime_manager_fields_on_instances(tmp_path, monkeypatch):
    fixture_root = tmp_path / "paper_validation_btcusd"
    create_monitor_fixture(fixture_root, "healthy", symbol="BTC/USD")
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
                    "decision_log_path": str(fixture_root / "decisions.csv"),
                    "fill_log_path": str(fixture_root / "fills.csv"),
                    "snapshot_log_path": str(fixture_root / "daily_snapshot.csv"),
                }
            ],
            "recent_sessions": [],
            "lifecycle_events": [
                {
                    "timestamp_utc": "2026-04-28T02:00:00+00:00",
                    "symbol": "BTC/USD",
                    "session_id": "session-btc",
                    "event_type": "running",
                    "message": "Runtime is running.",
                    "source": "runtime_manager",
                }
            ],
            "recent_control_actions": [
                {
                    "action_id": "btcusd-start",
                    "symbol": "BTC/USD",
                    "asset_class": "crypto",
                    "requested_action": "start",
                    "mode_context": "live",
                    "requested_at_utc": "2026-04-28T02:00:00+00:00",
                    "requested_from": "dashboard",
                    "confirmation_state": "confirmed",
                    "outcome_state": "succeeded",
                    "outcome_message": "Runtime start succeeded.",
                    "runtime_session_id": "session-btc",
                }
            ],
        },
    )
    monkeypatch.setenv("RUNTIME_REGISTRY_PATH", str(runtime_registry_path))
    config = load_monitor_configuration(symbols=("BTC/USD",), base_dir=tmp_path)
    app = create_app(instances=config.instances)
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    item = payload["instances"][0]

    assert item["runtime_state"] == "running"
    assert item["runtime_status_message"] == "Runtime is running."
    assert item["runtime_session_id"] == "session-btc"
    assert item["runtime_pid"] == 2468
    assert item["runtime_started_at_utc"] == "2026-04-28T01:55:00+00:00"
    assert item["runtime_last_seen_utc"] == "2026-04-28T02:00:00+00:00"
    assert item["last_lifecycle_event"] == "running"
    assert item["is_fresh_runtime_session"] is True
    assert item["control_asset_class"] == "crypto"
    assert item["control_mode_context"] == "live"
    assert item["control_runtime_state"] == "running"
    assert item["can_start"] is False
    assert item["can_stop"] is True
    assert item["can_restart"] is True
    assert item["requires_live_confirmation"] is True
    assert payload["recent_control_actions"][0]["requested_action"] == "start"
    assert payload["recent_control_actions"][0]["symbol"] == "BTC/USD"


def test_dashboard_contract_control_routes_return_operator_visible_results(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "healthy", symbol="BTC/USD")
    config = make_bot_config(symbols=("BTC/USD",))

    def fake_start_action(config, symbol, **kwargs):
        del config, kwargs
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

    app = create_app(
        instances=(
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
        ),
        config=config,
        start_action_runner=fake_start_action,
    )
    client = app.test_client()

    response = client.post("/control/start", data={"symbol": "BTC/USD", "mode_context": "live"})
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["symbol"] == "BTC/USD"
    assert payload["requested_action"] == "start"
    assert payload["outcome_state"] == "succeeded"
    assert payload["outcome_message"] == "Runtime is running."


def test_dashboard_contract_shows_stopped_runtime_as_stopped_not_stale(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "stale", symbol="BTC/USD")
    app = create_app(
        instances=(
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
                is_fresh_runtime_session=False,
            ),
        )
    )
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert payload["aggregate_state"] == "stopped"
    assert payload["instances"][0]["status"]["state"] == "stopped"
    assert "Runtime stopped by operator." in page_text
    assert "lifecycle stopped" in page_text


def test_dashboard_contract_prefers_fresh_runtime_session_over_old_failed_logs(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "failed", symbol="BTC/USD")
    runtime_started_at = (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat()
    app = create_app(
        instances=(
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
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert payload["aggregate_state"] == "running"
    assert payload["instances"][0]["status"]["state"] == "running"
    assert payload["instances"][0]["is_fresh_runtime_session"] is True
    assert "fresh session" in page_text


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


def test_dashboard_contract_exposes_notes_separately_from_issues(tmp_path):
    paths = create_monitor_fixture(tmp_path / "btc", "no_recent_fill", symbol="BTC/USD")
    now = datetime.now(timezone.utc)
    paths["snapshot"].write_text(
        "\n".join(
            [
                "date,mode,symbol,portfolio_value,cash,position_qty,day_pnl",
                f"{now.isoformat()},live,BTC/USD,99.0,80.0,2.0,-0.5",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(
        instances=(
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
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert any(note["category"] == "negative_pnl" for note in payload["notes"])
    assert not any(issue["category"] == "negative_pnl" for issue in payload["issues"])
    assert "Recent Notes" in page_text


def test_dashboard_contract_exposes_active_and_historical_context_separately(tmp_path):
    current_paths = create_monitor_fixture(tmp_path / "current", "healthy", symbol="BTC/USD")
    archived_paths = create_monitor_fixture(tmp_path / "history", "archived_failed", symbol="ETH/USD")
    app = create_app(
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
    )
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    assert payload["aggregate_state"] in {"paper", "running"}
    assert payload["historical_context"]["historical_instance_count"] == 1
    assert payload["historical_context"]["historical_issue_count"] >= 1
    assert "Historical Context" in page_text


def test_dashboard_contract_renders_stale_and_no_headline_sentiment_states(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stale_observed_at = (now - timedelta(hours=5)).isoformat()
    fresh_observed_at = now.isoformat()
    stale_paths = create_monitor_fixture(tmp_path / "stale_sentiment", "healthy", symbol="BTC/USD")
    fallback_paths = create_monitor_fixture(tmp_path / "no_headlines", "healthy", symbol="ETH/USD")
    stale_paths["decisions"].write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,sentiment_availability_state,sentiment_is_fallback,sentiment_observed_at,headline_count,headline_preview,sentiment_window_start,sentiment_window_end,quantity,portfolio_value,cash,reason,result",
                f"{now.isoformat()},live,BTC/USD,crypto,hold,model,0.7,external,0.8,positive,news_scored,false,{stale_observed_at},3,\"[\"\"H1\"\",\"\"H2\"\",\"\"H3\"\"]\",2026-04-23,2026-04-26,0,100,90,hold,skipped",
            ]
        ),
        encoding="utf-8",
    )
    fallback_paths["decisions"].write_text(
        "\n".join(
            [
                "timestamp,mode,symbol,asset_class,action,action_source,model_prob_up,sentiment_source,sentiment_probability,sentiment_label,sentiment_availability_state,sentiment_is_fallback,sentiment_observed_at,headline_count,headline_preview,sentiment_window_start,sentiment_window_end,quantity,portfolio_value,cash,reason,result",
                f"{now.isoformat()},live,ETH/USD,crypto,hold,model,0.6,external,0.0,neutral,,false,{fresh_observed_at},0,[],2026-04-23,2026-04-26,0,100,90,hold,skipped",
            ]
        ),
        encoding="utf-8",
    )
    app = create_app(
        instances=(
            DashboardInstance(
                label="BTC/USD",
                symbols=("BTC/USD",),
                asset_classes=("crypto",),
                decision_log_path=stale_paths["decisions"],
                fill_log_path=stale_paths["fills"],
                snapshot_log_path=stale_paths["snapshot"],
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
    )
    client = app.test_client()

    payload = client.get("/api/status").get_json()
    page_text = client.get("/").get_data(as_text=True)

    stale_item = next(item for item in payload["instances"] if item["label"] == "BTC/USD")
    no_headline_item = next(item for item in payload["instances"] if item["label"] == "ETH/USD")

    assert stale_item["sentiment_availability_state"] == "stale_news_scored"
    assert stale_item["sentiment_is_stale"] is True
    assert no_headline_item["sentiment_availability_state"] == "no_headlines"
    assert "No recent headlines were available for sentiment scoring." in page_text
    assert "Stale" in page_text
