from __future__ import annotations

from pathlib import Path

from tradingbot.app.runtime_manager import (
    DEFAULT_RECENT_SESSIONS_LIMIT,
    LifecycleEvent,
    ManagedRuntime,
    RuntimeRegistry,
    RuntimeSession,
    add_runtime_session,
    load_runtime_registry,
    register_managed_runtime,
    runtime_registry_from_dict,
    runtime_registry_to_dict,
    runtime_state_index,
    save_runtime_registry,
)


def _runtime(symbol: str = "BTC/USD", **overrides) -> ManagedRuntime:
    payload = {
        "symbol": symbol,
        "instance_label": symbol,
        "mode": "live",
        "lifecycle_state": "running",
        "session_id": f"session-{symbol.replace('/', '').lower()}",
        "pid": 1234,
        "started_at_utc": "2026-04-28T02:00:00+00:00",
        "last_seen_utc": "2026-04-28T02:05:00+00:00",
        "stop_requested_at_utc": "",
        "last_exit_code": None,
        "failure_reason": "",
        "decision_log_path": "logs/runtime/decisions.csv",
        "fill_log_path": "logs/runtime/fills.csv",
        "snapshot_log_path": "logs/runtime/daily_snapshot.csv",
    }
    payload.update(overrides)
    return ManagedRuntime(**payload)


def _session(symbol: str = "BTC/USD", session_id: str = "session-1", **overrides) -> RuntimeSession:
    payload = {
        "session_id": session_id,
        "symbol": symbol,
        "mode": "live",
        "launch_command": ("python", "-m", "tradingbot.app.main", "--mode", "live"),
        "launch_env_scope": {"SYMBOLS": symbol},
        "started_at_utc": "2026-04-28T02:00:00+00:00",
        "ended_at_utc": "",
        "exit_code": None,
        "end_reason": "",
        "was_live_mode": True,
        "was_manual_recovery": False,
    }
    payload.update(overrides)
    return RuntimeSession(**payload)


def _event(symbol: str = "BTC/USD", session_id: str = "session-1", **overrides) -> LifecycleEvent:
    payload = {
        "timestamp_utc": "2026-04-28T02:05:00+00:00",
        "symbol": symbol,
        "session_id": session_id,
        "event_type": "started",
        "message": "Runtime started.",
        "source": "runtime_manager",
    }
    payload.update(overrides)
    return LifecycleEvent(**payload)


def test_runtime_registry_round_trips_serialized_dataclasses():
    registry = RuntimeRegistry(
        updated_at_utc="2026-04-28T02:06:00+00:00",
        managed_runtimes=(_runtime(),),
        recent_sessions=(_session(),),
        lifecycle_events=(_event(),),
    )

    restored = runtime_registry_from_dict(runtime_registry_to_dict(registry))

    assert restored.registry_version == registry.registry_version
    assert restored.managed_runtimes == registry.managed_runtimes
    assert restored.recent_sessions == registry.recent_sessions
    assert restored.lifecycle_events == registry.lifecycle_events


def test_runtime_registry_save_and_load_preserves_contents(tmp_path: Path):
    path = tmp_path / "runtime" / "runtime_registry.json"
    registry = RuntimeRegistry(
        updated_at_utc="2026-04-28T02:06:00+00:00",
        managed_runtimes=(_runtime(),),
        recent_sessions=(_session(),),
        lifecycle_events=(_event(),),
    )

    save_runtime_registry(path, registry)
    loaded = load_runtime_registry(path)

    assert path.exists()
    assert loaded.managed_runtimes == registry.managed_runtimes
    assert loaded.recent_sessions == registry.recent_sessions
    assert loaded.lifecycle_events == registry.lifecycle_events


def test_register_managed_runtime_keeps_one_authoritative_runtime_per_symbol():
    registry = RuntimeRegistry(managed_runtimes=(_runtime(pid=1111), _runtime("ETH/USD", pid=2222)))

    updated = register_managed_runtime(
        registry,
        _runtime(pid=3333, session_id="session-btc-new"),
        event=_event(session_id="session-btc-new"),
    )

    index = runtime_state_index(updated)
    assert set(index) == {"BTC/USD", "ETH/USD"}
    assert index["BTC/USD"].pid == 3333
    assert index["BTC/USD"].session_id == "session-btc-new"
    assert len(updated.lifecycle_events) == 1


def test_add_runtime_session_applies_bounded_recent_session_limit():
    registry = RuntimeRegistry()

    for session_number in range(4):
        registry = add_runtime_session(
            registry,
            _session(session_id=f"session-{session_number}"),
            recent_limit=2,
        )

    assert [session.session_id for session in registry.recent_sessions] == ["session-2", "session-3"]


def test_add_runtime_session_ignores_non_positive_limit():
    registry = RuntimeRegistry()

    for session_number in range(DEFAULT_RECENT_SESSIONS_LIMIT + 2):
        registry = add_runtime_session(
            registry,
            _session(session_id=f"session-{session_number}"),
            recent_limit=0,
        )

    assert len(registry.recent_sessions) == DEFAULT_RECENT_SESSIONS_LIMIT
    assert registry.recent_sessions[0].session_id == "session-2"
    assert registry.recent_sessions[-1].session_id == f"session-{DEFAULT_RECENT_SESSIONS_LIMIT + 1}"
