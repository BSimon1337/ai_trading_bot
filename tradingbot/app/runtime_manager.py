from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNTIME_REGISTRY_VERSION = 1
DEFAULT_RECENT_SESSIONS_LIMIT = 25


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ManagedRuntime:
    symbol: str
    instance_label: str
    mode: str
    lifecycle_state: str
    session_id: str
    pid: int | None = None
    started_at_utc: str = ""
    last_seen_utc: str = ""
    stop_requested_at_utc: str = ""
    last_exit_code: int | None = None
    failure_reason: str = ""
    decision_log_path: str = ""
    fill_log_path: str = ""
    snapshot_log_path: str = ""


@dataclass(frozen=True)
class RuntimeSession:
    session_id: str
    symbol: str
    mode: str
    launch_command: tuple[str, ...] = ()
    launch_env_scope: dict[str, str] = field(default_factory=dict)
    started_at_utc: str = ""
    ended_at_utc: str = ""
    exit_code: int | None = None
    end_reason: str = ""
    was_live_mode: bool = False
    was_manual_recovery: bool = False


@dataclass(frozen=True)
class LifecycleEvent:
    timestamp_utc: str
    symbol: str
    session_id: str
    event_type: str
    message: str
    source: str


@dataclass(frozen=True)
class RuntimeRegistry:
    registry_version: int = RUNTIME_REGISTRY_VERSION
    updated_at_utc: str = field(default_factory=utc_now_iso)
    managed_runtimes: tuple[ManagedRuntime, ...] = ()
    recent_sessions: tuple[RuntimeSession, ...] = ()
    lifecycle_events: tuple[LifecycleEvent, ...] = ()


def _coerce_sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _coerce_recent_limit(value: int) -> int:
    return value if value > 0 else DEFAULT_RECENT_SESSIONS_LIMIT


def _runtime_from_dict(value: dict[str, Any]) -> ManagedRuntime:
    return ManagedRuntime(
        symbol=str(value.get("symbol", "")),
        instance_label=str(value.get("instance_label", "")),
        mode=str(value.get("mode", "")),
        lifecycle_state=str(value.get("lifecycle_state", "")),
        session_id=str(value.get("session_id", "")),
        pid=value.get("pid"),
        started_at_utc=str(value.get("started_at_utc", "")),
        last_seen_utc=str(value.get("last_seen_utc", "")),
        stop_requested_at_utc=str(value.get("stop_requested_at_utc", "")),
        last_exit_code=value.get("last_exit_code"),
        failure_reason=str(value.get("failure_reason", "")),
        decision_log_path=str(value.get("decision_log_path", "")),
        fill_log_path=str(value.get("fill_log_path", "")),
        snapshot_log_path=str(value.get("snapshot_log_path", "")),
    )


def _session_from_dict(value: dict[str, Any]) -> RuntimeSession:
    return RuntimeSession(
        session_id=str(value.get("session_id", "")),
        symbol=str(value.get("symbol", "")),
        mode=str(value.get("mode", "")),
        launch_command=tuple(str(item) for item in _coerce_sequence(value.get("launch_command"))),
        launch_env_scope={str(key): str(item) for key, item in dict(value.get("launch_env_scope", {})).items()},
        started_at_utc=str(value.get("started_at_utc", "")),
        ended_at_utc=str(value.get("ended_at_utc", "")),
        exit_code=value.get("exit_code"),
        end_reason=str(value.get("end_reason", "")),
        was_live_mode=bool(value.get("was_live_mode", False)),
        was_manual_recovery=bool(value.get("was_manual_recovery", False)),
    )


def _event_from_dict(value: dict[str, Any]) -> LifecycleEvent:
    return LifecycleEvent(
        timestamp_utc=str(value.get("timestamp_utc", "")),
        symbol=str(value.get("symbol", "")),
        session_id=str(value.get("session_id", "")),
        event_type=str(value.get("event_type", "")),
        message=str(value.get("message", "")),
        source=str(value.get("source", "")),
    )


def empty_runtime_registry() -> RuntimeRegistry:
    return RuntimeRegistry()


def runtime_registry_to_dict(registry: RuntimeRegistry) -> dict[str, Any]:
    return {
        "registry_version": registry.registry_version,
        "updated_at_utc": registry.updated_at_utc,
        "managed_runtimes": [asdict(runtime) for runtime in registry.managed_runtimes],
        "recent_sessions": [
            {
                **asdict(session),
                "launch_command": list(session.launch_command),
            }
            for session in registry.recent_sessions
        ],
        "lifecycle_events": [asdict(event) for event in registry.lifecycle_events],
    }


def runtime_registry_from_dict(payload: dict[str, Any]) -> RuntimeRegistry:
    return RuntimeRegistry(
        registry_version=int(payload.get("registry_version", RUNTIME_REGISTRY_VERSION)),
        updated_at_utc=str(payload.get("updated_at_utc", "")) or utc_now_iso(),
        managed_runtimes=tuple(
            _runtime_from_dict(item) for item in _coerce_sequence(payload.get("managed_runtimes")) if isinstance(item, dict)
        ),
        recent_sessions=tuple(
            _session_from_dict(item) for item in _coerce_sequence(payload.get("recent_sessions")) if isinstance(item, dict)
        ),
        lifecycle_events=tuple(
            _event_from_dict(item) for item in _coerce_sequence(payload.get("lifecycle_events")) if isinstance(item, dict)
        ),
    )


def load_runtime_registry(path: Path) -> RuntimeRegistry:
    path = Path(path)
    if not path.exists():
        return empty_runtime_registry()
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Runtime registry at {path} must contain a JSON object.")
    return runtime_registry_from_dict(payload)


def save_runtime_registry(path: Path, registry: RuntimeRegistry) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(runtime_registry_to_dict(registry), handle, indent=2, sort_keys=True)


def register_managed_runtime(
    registry: RuntimeRegistry,
    runtime: ManagedRuntime,
    *,
    event: LifecycleEvent | None = None,
) -> RuntimeRegistry:
    runtimes = [item for item in registry.managed_runtimes if item.symbol != runtime.symbol]
    runtimes.append(runtime)
    events = list(registry.lifecycle_events)
    if event is not None:
        events.append(event)
    return RuntimeRegistry(
        registry_version=registry.registry_version,
        updated_at_utc=utc_now_iso(),
        managed_runtimes=tuple(sorted(runtimes, key=lambda item: item.symbol)),
        recent_sessions=registry.recent_sessions,
        lifecycle_events=tuple(events[-DEFAULT_RECENT_SESSIONS_LIMIT:]),
    )


def add_runtime_session(
    registry: RuntimeRegistry,
    session: RuntimeSession,
    *,
    recent_limit: int = DEFAULT_RECENT_SESSIONS_LIMIT,
) -> RuntimeRegistry:
    recent_limit = _coerce_recent_limit(recent_limit)
    sessions = [item for item in registry.recent_sessions if item.session_id != session.session_id]
    sessions.append(session)
    return RuntimeRegistry(
        registry_version=registry.registry_version,
        updated_at_utc=utc_now_iso(),
        managed_runtimes=registry.managed_runtimes,
        recent_sessions=tuple(sessions[-recent_limit:]),
        lifecycle_events=registry.lifecycle_events,
    )


def runtime_state_index(registry: RuntimeRegistry) -> dict[str, ManagedRuntime]:
    return {runtime.symbol: runtime for runtime in registry.managed_runtimes}
