from __future__ import annotations

from pathlib import Path

from tradingbot.app.runtime_manager import (
    DEFAULT_RECENT_SESSIONS_LIMIT,
    LifecycleEvent,
    ManagedRuntime,
    RuntimeRegistry,
    RuntimeSession,
    add_runtime_session,
    build_runtime_launch_command,
    build_runtime_launch_env,
    build_symbol_runtime_config,
    load_runtime_registry,
    register_managed_runtime,
    start_managed_runtime,
    start_managed_runtimes,
    runtime_registry_from_dict,
    runtime_registry_to_dict,
    runtime_state_index,
    save_runtime_registry,
    symbol_log_scope,
)
from tests.conftest import make_bot_config


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


def test_build_symbol_runtime_config_uses_symbol_scoped_log_paths():
    config = make_bot_config(symbols=("BTC/USD", "ETH/USD"))

    symbol_config = build_symbol_runtime_config(config, "ETH/USD")

    assert symbol_config.symbol == "ETH/USD"
    assert symbol_config.symbols == ("ETH/USD",)
    assert symbol_config.decision_log_path.endswith("paper_validation_ethusd\\decisions.csv")
    assert symbol_config.fill_log_path.endswith("paper_validation_ethusd\\fills.csv")
    assert symbol_config.daily_snapshot_path.endswith("paper_validation_ethusd\\daily_snapshot.csv")


def test_symbol_log_scope_preserves_distinct_symbol_scoped_paths():
    btc_scope = symbol_log_scope("BTC/USD")
    eth_scope = symbol_log_scope("ETH/USD")

    assert btc_scope.decision_log_path != eth_scope.decision_log_path
    assert "paper_validation_btcusd" in btc_scope.decision_log_path
    assert "paper_validation_ethusd" in eth_scope.decision_log_path


def test_build_runtime_launch_env_records_only_symbol_scoped_runtime_inputs():
    config = make_bot_config(runtime_registry_path="logs/test/runtime_registry.json")

    environment, env_scope, log_scope = build_runtime_launch_env(config, "BTC/USD")

    assert environment["SYMBOL"] == "BTC/USD"
    assert environment["SYMBOLS"] == "BTC/USD"
    assert environment["RUNTIME_REGISTRY_PATH"] == "logs/test/runtime_registry.json"
    assert env_scope["DECISION_LOG_PATH"] == log_scope.decision_log_path
    assert "API_KEY" not in env_scope
    assert "API_SECRET" not in env_scope


def test_start_managed_runtime_registers_running_state_and_session(tmp_path: Path):
    registry_path = tmp_path / "runtime" / "runtime_registry.json"
    config = make_bot_config(runtime_registry_path=str(registry_path))

    class FakeProcess:
        pid = 4567

    calls: dict[str, object] = {}

    def fake_popen(command, cwd=None, env=None):
        calls["command"] = command
        calls["cwd"] = cwd
        calls["env"] = env
        return FakeProcess()

    result = start_managed_runtime(
        config,
        "BTC/USD",
        registry_path=registry_path,
        popen_factory=fake_popen,
        cwd=tmp_path,
    )

    registry = load_runtime_registry(registry_path)
    runtime = runtime_state_index(registry)["BTC/USD"]

    assert result.runtime_state == "running"
    assert result.pid == 4567
    assert runtime.lifecycle_state == "running"
    assert runtime.pid == 4567
    assert registry.recent_sessions[-1].session_id == result.session_id
    assert calls["command"] == list(build_runtime_launch_command(mode="live"))
    assert calls["cwd"] == str(tmp_path)
    assert calls["env"]["SYMBOLS"] == "BTC/USD"


def test_start_managed_runtimes_tracks_independent_symbol_sessions(tmp_path: Path):
    registry_path = tmp_path / "runtime" / "runtime_registry.json"
    config = make_bot_config(runtime_registry_path=str(registry_path), symbols=("BTC/USD", "ETH/USD"))

    class FakeProcess:
        def __init__(self, pid):
            self.pid = pid

    pids = iter((1111, 2222))

    def fake_popen(command, cwd=None, env=None):
        del command, cwd, env
        return FakeProcess(next(pids))

    results = start_managed_runtimes(
        config,
        ("BTC/USD", "ETH/USD"),
        registry_path=registry_path,
        popen_factory=fake_popen,
        cwd=tmp_path,
    )

    registry = load_runtime_registry(registry_path)
    runtime_index = runtime_state_index(registry)

    assert len(results) == 2
    assert runtime_index["BTC/USD"].pid == 1111
    assert runtime_index["ETH/USD"].pid == 2222
    assert runtime_index["BTC/USD"].session_id != runtime_index["ETH/USD"].session_id
