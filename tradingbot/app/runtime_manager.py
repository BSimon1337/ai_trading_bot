from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from tradingbot.config.settings import BotConfig, infer_asset_class
from tradingbot.execution.safeguards import RuntimeGuardrailError, resolve_runtime_state


RUNTIME_REGISTRY_VERSION = 1
DEFAULT_RECENT_SESSIONS_LIMIT = 25
DEFAULT_RECENT_CONTROL_ACTIONS_LIMIT = 25


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
class ManagedControlAction:
    action_id: str
    symbol: str
    asset_class: str
    requested_action: str
    mode_context: str
    requested_at_utc: str
    requested_from: str = "dashboard"
    confirmation_state: str = "not_required"
    outcome_state: str = "pending"
    outcome_message: str = ""
    runtime_session_id: str = ""


@dataclass(frozen=True)
class RuntimeRegistry:
    registry_version: int = RUNTIME_REGISTRY_VERSION
    updated_at_utc: str = field(default_factory=utc_now_iso)
    managed_runtimes: tuple[ManagedRuntime, ...] = ()
    recent_sessions: tuple[RuntimeSession, ...] = ()
    lifecycle_events: tuple[LifecycleEvent, ...] = ()
    recent_control_actions: tuple[ManagedControlAction, ...] = ()


@dataclass(frozen=True)
class RuntimeLogScope:
    decision_log_path: str
    fill_log_path: str
    snapshot_log_path: str


@dataclass(frozen=True)
class RuntimeStartResult:
    symbol: str
    session_id: str
    runtime_state: str
    started_at_utc: str
    pid: int | None
    status_message: str
    runtime: ManagedRuntime
    session: RuntimeSession


@dataclass(frozen=True)
class RuntimeStopResult:
    symbol: str
    previous_session_id: str
    runtime_state: str
    stopped_at_utc: str
    status_message: str
    runtime: ManagedRuntime
    session: RuntimeSession | None


@dataclass(frozen=True)
class RuntimeRestartResult:
    symbol: str
    old_session_id: str
    new_session_id: str
    runtime_state: str
    started_at_utc: str
    status_message: str
    runtime: ManagedRuntime
    session: RuntimeSession


def _control_outcome_from_runtime_state(runtime_state: str) -> str:
    if runtime_state in {"running", "stopped"}:
        return "succeeded"
    if runtime_state in {"failed", "blocked"}:
        return "failed"
    return "pending"


def _requested_mode_context(mode: str | None, config: BotConfig) -> str:
    normalized_mode = (mode or "").strip().lower()
    if normalized_mode in {"live", "paper"}:
        return normalized_mode
    return "paper" if config.paper else "live"


def _save_control_action(
    registry_file: Path,
    config: BotConfig,
    action: ManagedControlAction,
) -> ManagedControlAction:
    registry = load_runtime_registry(registry_file)
    registry = add_control_action(
        registry,
        action,
        recent_limit=config.runtime_recent_control_actions_limit,
    )
    save_runtime_registry(registry_file, registry)
    return action


def _coerce_sequence(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _coerce_recent_limit(value: int) -> int:
    return value if value > 0 else DEFAULT_RECENT_SESSIONS_LIMIT


def _sanitize_symbol_for_path(symbol: str) -> str:
    return "".join(character for character in symbol.strip().lower() if character.isalnum())


def symbol_log_scope(symbol: str, *, base_dir: Path = Path("logs")) -> RuntimeLogScope:
    normalized_symbol = symbol.strip()
    suffix = "" if normalized_symbol.upper() == "SPY" else f"_{_sanitize_symbol_for_path(normalized_symbol)}"
    root = Path(base_dir) / f"paper_validation{suffix}"
    return RuntimeLogScope(
        decision_log_path=str(root / "decisions.csv"),
        fill_log_path=str(root / "fills.csv"),
        snapshot_log_path=str(root / "daily_snapshot.csv"),
    )


def create_runtime_session_id(symbol: str) -> str:
    slug = _sanitize_symbol_for_path(symbol) or "symbol"
    return f"{slug}-{uuid4().hex[:12]}"


def _terminate_process(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)


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


def _control_action_from_dict(value: dict[str, Any]) -> ManagedControlAction:
    return ManagedControlAction(
        action_id=str(value.get("action_id", "")),
        symbol=str(value.get("symbol", "")),
        asset_class=str(value.get("asset_class", "")),
        requested_action=str(value.get("requested_action", "")),
        mode_context=str(value.get("mode_context", "")),
        requested_at_utc=str(value.get("requested_at_utc", "")),
        requested_from=str(value.get("requested_from", "dashboard")),
        confirmation_state=str(value.get("confirmation_state", "not_required")),
        outcome_state=str(value.get("outcome_state", "pending")),
        outcome_message=str(value.get("outcome_message", "")),
        runtime_session_id=str(value.get("runtime_session_id", "")),
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
        "recent_control_actions": [asdict(action) for action in registry.recent_control_actions],
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
        recent_control_actions=tuple(
            _control_action_from_dict(item)
            for item in _coerce_sequence(payload.get("recent_control_actions"))
            if isinstance(item, dict)
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
        recent_control_actions=registry.recent_control_actions,
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
        recent_control_actions=registry.recent_control_actions,
    )


def add_control_action(
    registry: RuntimeRegistry,
    action: ManagedControlAction,
    *,
    recent_limit: int = DEFAULT_RECENT_CONTROL_ACTIONS_LIMIT,
) -> RuntimeRegistry:
    recent_limit = _coerce_recent_limit(recent_limit)
    actions = [item for item in registry.recent_control_actions if item.action_id != action.action_id]
    actions.append(action)
    return RuntimeRegistry(
        registry_version=registry.registry_version,
        updated_at_utc=utc_now_iso(),
        managed_runtimes=registry.managed_runtimes,
        recent_sessions=registry.recent_sessions,
        lifecycle_events=registry.lifecycle_events,
        recent_control_actions=tuple(actions[-recent_limit:]),
    )


def runtime_state_index(registry: RuntimeRegistry) -> dict[str, ManagedRuntime]:
    return {runtime.symbol: runtime for runtime in registry.managed_runtimes}


def lifecycle_event_index(registry: RuntimeRegistry) -> dict[str, LifecycleEvent]:
    latest: dict[str, LifecycleEvent] = {}
    for event in registry.lifecycle_events:
        latest[event.symbol] = event
    return latest


def current_runtime_for_symbol(registry: RuntimeRegistry, symbol: str) -> ManagedRuntime | None:
    for runtime in registry.managed_runtimes:
        if runtime.symbol == symbol:
            return runtime
    return None


def current_session_for_runtime(registry: RuntimeRegistry, runtime: ManagedRuntime) -> RuntimeSession | None:
    for session in reversed(registry.recent_sessions):
        if session.session_id == runtime.session_id:
            return session
    return None


def build_symbol_runtime_config(config: BotConfig, symbol: str) -> BotConfig:
    log_scope = symbol_log_scope(symbol)
    return BotConfig(
        **{
            **config.__dict__,
            "symbol": symbol,
            "symbols": (symbol,),
            "decision_log_path": log_scope.decision_log_path,
            "fill_log_path": log_scope.fill_log_path,
            "daily_snapshot_path": log_scope.snapshot_log_path,
        }
    )


def build_runtime_launch_command(
    *,
    python_executable: str | None = None,
    mode: str = "live",
) -> tuple[str, ...]:
    return (
        python_executable or sys.executable,
        "-m",
        "tradingbot.app.main",
        "--mode",
        mode,
    )


def build_runtime_launch_env(
    config: BotConfig,
    symbol: str,
) -> tuple[dict[str, str], dict[str, str], RuntimeLogScope]:
    symbol_config = build_symbol_runtime_config(config, symbol)
    log_scope = RuntimeLogScope(
        decision_log_path=symbol_config.decision_log_path,
        fill_log_path=symbol_config.fill_log_path,
        snapshot_log_path=symbol_config.daily_snapshot_path,
    )
    launch_env_scope = {
        "SYMBOL": symbol,
        "SYMBOLS": symbol,
        "CRYPTO_SYMBOLS": "",
        "ALPACA_CRYPTO_UNIVERSE": "none",
        "DECISION_LOG_PATH": log_scope.decision_log_path,
        "FILL_LOG_PATH": log_scope.fill_log_path,
        "DAILY_SNAPSHOT_PATH": log_scope.snapshot_log_path,
        "RUNTIME_REGISTRY_PATH": config.runtime_registry_path,
    }
    if infer_asset_class(symbol) == "crypto":
        launch_env_scope["SYMBOL"] = symbol
        launch_env_scope["SYMBOLS"] = symbol
    environment = os.environ.copy()
    environment.update(launch_env_scope)
    return environment, launch_env_scope, log_scope


def start_managed_runtime(
    config: BotConfig,
    symbol: str,
    *,
    mode: str = "live",
    registry_path: Path | None = None,
    popen_factory: Any = subprocess.Popen,
    cwd: Path | None = None,
    python_executable: str | None = None,
    was_manual_recovery: bool = False,
) -> RuntimeStartResult:
    registry_file = Path(registry_path or config.runtime_registry_path)
    registry = load_runtime_registry(registry_file)
    started_at = utc_now_iso()
    session_id = create_runtime_session_id(symbol)
    try:
        runtime_state = resolve_runtime_state(config, mode)
    except RuntimeGuardrailError as exc:
        command = build_runtime_launch_command(python_executable=python_executable, mode=mode)
        environment, launch_env_scope, log_scope = build_runtime_launch_env(config, symbol)
        failed_session = RuntimeSession(
            session_id=session_id,
            symbol=symbol,
            mode=mode,
            launch_command=command,
            launch_env_scope=launch_env_scope,
            started_at_utc=started_at,
            ended_at_utc=started_at,
            end_reason="guardrail_blocked",
            was_live_mode=False,
            was_manual_recovery=was_manual_recovery,
        )
        failed_runtime = ManagedRuntime(
            symbol=symbol,
            instance_label=symbol,
            mode=mode,
            lifecycle_state="failed",
            session_id=session_id,
            started_at_utc=started_at,
            last_seen_utc=started_at,
            failure_reason=str(exc),
            decision_log_path=log_scope.decision_log_path,
            fill_log_path=log_scope.fill_log_path,
            snapshot_log_path=log_scope.snapshot_log_path,
        )
        registry = add_runtime_session(registry, failed_session, recent_limit=config.runtime_recent_sessions_limit)
        registry = register_managed_runtime(
            registry,
            failed_runtime,
            event=LifecycleEvent(
                timestamp_utc=started_at,
                symbol=symbol,
                session_id=session_id,
                event_type="failed",
                message=str(exc),
                source="runtime_manager",
            ),
        )
        save_runtime_registry(registry_file, registry)
        return RuntimeStartResult(
            symbol=symbol,
            session_id=session_id,
            runtime_state="failed",
            started_at_utc=started_at,
            pid=None,
            status_message=str(exc),
            runtime=failed_runtime,
            session=failed_session,
        )

    actual_mode = runtime_state.execution_mode
    command = build_runtime_launch_command(python_executable=python_executable, mode=mode)
    environment, launch_env_scope, log_scope = build_runtime_launch_env(config, symbol)

    session = RuntimeSession(
        session_id=session_id,
        symbol=symbol,
        mode=actual_mode,
        launch_command=command,
        launch_env_scope=launch_env_scope,
        started_at_utc=started_at,
        was_live_mode=actual_mode == "live",
        was_manual_recovery=was_manual_recovery,
    )
    starting_runtime = ManagedRuntime(
        symbol=symbol,
        instance_label=symbol,
        mode=actual_mode,
        lifecycle_state="starting",
        session_id=session_id,
        started_at_utc=started_at,
        last_seen_utc=started_at,
        decision_log_path=log_scope.decision_log_path,
        fill_log_path=log_scope.fill_log_path,
        snapshot_log_path=log_scope.snapshot_log_path,
    )
    registry = add_runtime_session(registry, session, recent_limit=config.runtime_recent_sessions_limit)
    registry = register_managed_runtime(
        registry,
        starting_runtime,
        event=LifecycleEvent(
            timestamp_utc=started_at,
            symbol=symbol,
            session_id=session_id,
            event_type="start_requested",
            message="Runtime start requested.",
            source="runtime_manager",
        ),
    )
    save_runtime_registry(registry_file, registry)

    try:
        process = popen_factory(
            list(command),
            cwd=str(cwd or Path.cwd()),
            env=environment,
        )
    except Exception as exc:
        failed_at = utc_now_iso()
        failed_session = RuntimeSession(
            **{
                **session.__dict__,
                "ended_at_utc": failed_at,
                "end_reason": "launch_failed",
            }
        )
        failed_runtime = ManagedRuntime(
            **{
                **starting_runtime.__dict__,
                "lifecycle_state": "failed",
                "last_seen_utc": failed_at,
                "failure_reason": str(exc),
            }
        )
        registry = add_runtime_session(registry, failed_session, recent_limit=config.runtime_recent_sessions_limit)
        registry = register_managed_runtime(
            registry,
            failed_runtime,
            event=LifecycleEvent(
                timestamp_utc=failed_at,
                symbol=symbol,
                session_id=session_id,
                event_type="failed",
                message=str(exc),
                source="runtime_manager",
            ),
        )
        save_runtime_registry(registry_file, registry)
        return RuntimeStartResult(
            symbol=symbol,
            session_id=session_id,
            runtime_state="failed",
            started_at_utc=started_at,
            pid=None,
            status_message=str(exc),
            runtime=failed_runtime,
            session=failed_session,
        )

    running_at = utc_now_iso()
    running_runtime = ManagedRuntime(
        **{
            **starting_runtime.__dict__,
            "lifecycle_state": "running",
            "pid": getattr(process, "pid", None),
            "last_seen_utc": running_at,
        }
    )
    registry = register_managed_runtime(
        registry,
        running_runtime,
        event=LifecycleEvent(
            timestamp_utc=running_at,
            symbol=symbol,
            session_id=session_id,
            event_type="running",
            message="Runtime is running.",
            source="runtime_manager",
        ),
    )
    save_runtime_registry(registry_file, registry)
    return RuntimeStartResult(
        symbol=symbol,
        session_id=session_id,
        runtime_state="running",
        started_at_utc=started_at,
        pid=getattr(process, "pid", None),
        status_message="Runtime is running.",
        runtime=running_runtime,
        session=session,
    )


def start_managed_runtimes(
    config: BotConfig,
    symbols: tuple[str, ...],
    *,
    mode: str = "live",
    registry_path: Path | None = None,
    popen_factory: Any = subprocess.Popen,
    cwd: Path | None = None,
    python_executable: str | None = None,
) -> tuple[RuntimeStartResult, ...]:
    return tuple(
        start_managed_runtime(
            config,
            symbol,
            mode=mode,
            registry_path=registry_path,
            popen_factory=popen_factory,
            cwd=cwd,
            python_executable=python_executable,
        )
        for symbol in symbols
    )


def stop_managed_runtime(
    config: BotConfig,
    symbol: str,
    *,
    registry_path: Path | None = None,
    terminate_process: Any = _terminate_process,
    stop_reason: str = "operator_stop",
    status_message: str = "Runtime stopped by operator.",
) -> RuntimeStopResult:
    registry_file = Path(registry_path or config.runtime_registry_path)
    registry = load_runtime_registry(registry_file)
    runtime = current_runtime_for_symbol(registry, symbol)
    stopped_at = utc_now_iso()
    log_scope = symbol_log_scope(symbol)

    if runtime is None:
        stopped_runtime = ManagedRuntime(
            symbol=symbol,
            instance_label=symbol,
            mode="live",
            lifecycle_state="stopped",
            session_id="",
            started_at_utc="",
            last_seen_utc=stopped_at,
            stop_requested_at_utc=stopped_at,
            decision_log_path=log_scope.decision_log_path,
            fill_log_path=log_scope.fill_log_path,
            snapshot_log_path=log_scope.snapshot_log_path,
        )
        registry = register_managed_runtime(
            registry,
            stopped_runtime,
            event=LifecycleEvent(
                timestamp_utc=stopped_at,
                symbol=symbol,
                session_id="",
                event_type="stopped",
                message="Runtime was already stopped.",
                source="runtime_manager",
            ),
        )
        save_runtime_registry(registry_file, registry)
        return RuntimeStopResult(
            symbol=symbol,
            previous_session_id="",
            runtime_state="stopped",
            stopped_at_utc=stopped_at,
            status_message="Runtime was already stopped.",
            runtime=stopped_runtime,
            session=None,
        )

    session = current_session_for_runtime(registry, runtime)
    registry = register_managed_runtime(
        registry,
        ManagedRuntime(
            **{
                **runtime.__dict__,
                "lifecycle_state": "stopping",
                "stop_requested_at_utc": stopped_at,
                "last_seen_utc": stopped_at,
            }
        ),
        event=LifecycleEvent(
            timestamp_utc=stopped_at,
            symbol=symbol,
            session_id=runtime.session_id,
            event_type="stop_requested",
            message=status_message,
            source="runtime_manager",
        ),
    )

    stop_message = status_message
    if runtime.pid is not None:
        try:
            terminate_process(runtime.pid)
        except ProcessLookupError:
            stop_message = "Runtime process was already stopped."
        except Exception as exc:
            stop_message = str(exc)
            failed_runtime = ManagedRuntime(
                **{
                    **runtime.__dict__,
                    "lifecycle_state": "failed",
                    "stop_requested_at_utc": stopped_at,
                    "last_seen_utc": stopped_at,
                    "failure_reason": stop_message,
                }
            )
            registry = register_managed_runtime(
                registry,
                failed_runtime,
                event=LifecycleEvent(
                    timestamp_utc=stopped_at,
                    symbol=symbol,
                    session_id=runtime.session_id,
                    event_type="failed",
                    message=stop_message,
                    source="runtime_manager",
                ),
            )
            if session is not None:
                registry = add_runtime_session(
                    registry,
                    RuntimeSession(
                        **{
                            **session.__dict__,
                            "ended_at_utc": stopped_at,
                            "end_reason": "stop_failed",
                        }
                    ),
                    recent_limit=config.runtime_recent_sessions_limit,
                )
            save_runtime_registry(registry_file, registry)
            return RuntimeStopResult(
                symbol=symbol,
                previous_session_id=runtime.session_id,
                runtime_state="failed",
                stopped_at_utc=stopped_at,
                status_message=stop_message,
                runtime=failed_runtime,
                session=session,
            )

    stopped_runtime = ManagedRuntime(
        **{
            **runtime.__dict__,
            "lifecycle_state": "stopped",
            "pid": None,
            "stop_requested_at_utc": stopped_at,
            "last_seen_utc": stopped_at,
            "last_exit_code": 0,
            "failure_reason": "",
        }
    )
    registry = register_managed_runtime(
        registry,
        stopped_runtime,
        event=LifecycleEvent(
            timestamp_utc=stopped_at,
            symbol=symbol,
            session_id=runtime.session_id,
            event_type="stopped",
            message=stop_message,
            source="runtime_manager",
        ),
    )
    if session is not None:
        registry = add_runtime_session(
            registry,
            RuntimeSession(
                **{
                    **session.__dict__,
                    "ended_at_utc": stopped_at,
                    "exit_code": 0,
                    "end_reason": stop_reason,
                }
            ),
            recent_limit=config.runtime_recent_sessions_limit,
        )
    save_runtime_registry(registry_file, registry)
    return RuntimeStopResult(
        symbol=symbol,
        previous_session_id=runtime.session_id,
        runtime_state="stopped",
        stopped_at_utc=stopped_at,
        status_message=stop_message,
        runtime=stopped_runtime,
        session=session,
    )


def restart_managed_runtime(
    config: BotConfig,
    symbol: str,
    *,
    mode: str = "live",
    registry_path: Path | None = None,
    terminate_process: Any = _terminate_process,
    popen_factory: Any = subprocess.Popen,
    cwd: Path | None = None,
    python_executable: str | None = None,
) -> RuntimeRestartResult:
    registry_file = Path(registry_path or config.runtime_registry_path)
    registry = load_runtime_registry(registry_file)
    previous_runtime = current_runtime_for_symbol(registry, symbol)
    old_session_id = "" if previous_runtime is None else previous_runtime.session_id
    restart_requested_at = utc_now_iso()
    if previous_runtime is not None:
        registry = register_managed_runtime(
            registry,
            ManagedRuntime(
                **{
                    **previous_runtime.__dict__,
                    "lifecycle_state": "restarting",
                    "last_seen_utc": restart_requested_at,
                }
            ),
            event=LifecycleEvent(
                timestamp_utc=restart_requested_at,
                symbol=symbol,
                session_id=old_session_id,
                event_type="restart_requested",
                message="Runtime restart requested.",
                source="runtime_manager",
            ),
        )
        save_runtime_registry(registry_file, registry)
        stop_managed_runtime(
            config,
            symbol,
            registry_path=registry_file,
            terminate_process=terminate_process,
            stop_reason="restart_requested",
            status_message="Runtime restarting.",
        )

    start_result = start_managed_runtime(
        config,
        symbol,
        mode=mode,
        registry_path=registry_file,
        popen_factory=popen_factory,
        cwd=cwd,
        python_executable=python_executable,
        was_manual_recovery=True,
    )
    registry = load_runtime_registry(registry_file)
    registry = register_managed_runtime(
        registry,
        start_result.runtime,
        event=LifecycleEvent(
            timestamp_utc=utc_now_iso(),
            symbol=symbol,
            session_id=start_result.session_id,
            event_type="restarted",
            message=start_result.status_message,
            source="runtime_manager",
        ),
    )
    save_runtime_registry(registry_file, registry)
    return RuntimeRestartResult(
        symbol=symbol,
        old_session_id=old_session_id,
        new_session_id=start_result.session_id,
        runtime_state=start_result.runtime_state,
        started_at_utc=start_result.started_at_utc,
        status_message=start_result.status_message,
        runtime=start_result.runtime,
        session=start_result.session,
    )


def request_start_runtime_action(
    config: BotConfig,
    symbol: str,
    *,
    mode: str | None = None,
    registry_path: Path | None = None,
    popen_factory: Any = subprocess.Popen,
    cwd: Path | None = None,
    python_executable: str | None = None,
    requested_from: str = "dashboard",
    confirmation_state: str = "not_required",
) -> ManagedControlAction:
    registry_file = Path(registry_path or config.runtime_registry_path)
    current_runtime = current_runtime_for_symbol(load_runtime_registry(registry_file), symbol)
    mode_context = _requested_mode_context(mode, config)
    if requested_from == "dashboard" and mode_context == "live" and confirmation_state != "confirmed":
        return _save_control_action(
            registry_file,
            config,
            ManagedControlAction(
                action_id=uuid4().hex,
                symbol=symbol,
                asset_class=infer_asset_class(symbol),
                requested_action="start",
                mode_context=mode_context,
                requested_at_utc=utc_now_iso(),
                requested_from=requested_from,
                confirmation_state=confirmation_state,
                outcome_state="blocked",
                outcome_message=f"Live start requires confirmation. Enter {config.live_confirmation_token} to continue.",
                runtime_session_id="" if current_runtime is None else current_runtime.session_id,
            ),
        )
    if current_runtime is not None and current_runtime.lifecycle_state in {"starting", "running", "restarting", "stopping"}:
        return _save_control_action(
            registry_file,
            config,
            ManagedControlAction(
                action_id=uuid4().hex,
                symbol=symbol,
                asset_class=infer_asset_class(symbol),
                requested_action="start",
                mode_context=mode_context,
                requested_at_utc=utc_now_iso(),
                requested_from=requested_from,
                confirmation_state=confirmation_state,
                outcome_state="blocked",
                outcome_message=f"Runtime is already {current_runtime.lifecycle_state}.",
                runtime_session_id=current_runtime.session_id,
            ),
        )

    result = start_managed_runtime(
        config,
        symbol,
        mode=mode_context,
        registry_path=registry_file,
        popen_factory=popen_factory,
        cwd=cwd,
        python_executable=python_executable,
    )
    return _save_control_action(
        registry_file,
        config,
        ManagedControlAction(
            action_id=uuid4().hex,
            symbol=symbol,
            asset_class=infer_asset_class(symbol),
            requested_action="start",
            mode_context=mode_context,
            requested_at_utc=utc_now_iso(),
            requested_from=requested_from,
            confirmation_state=confirmation_state,
            outcome_state=_control_outcome_from_runtime_state(result.runtime_state),
            outcome_message=result.status_message,
            runtime_session_id=result.session_id,
        ),
    )


def request_stop_runtime_action(
    config: BotConfig,
    symbol: str,
    *,
    registry_path: Path | None = None,
    terminate_process: Any = _terminate_process,
    requested_from: str = "dashboard",
) -> ManagedControlAction:
    registry_file = Path(registry_path or config.runtime_registry_path)
    current_runtime = current_runtime_for_symbol(load_runtime_registry(registry_file), symbol)
    mode_context = "paper" if config.paper else "live"
    if current_runtime is None or current_runtime.lifecycle_state == "stopped":
        return _save_control_action(
            registry_file,
            config,
            ManagedControlAction(
                action_id=uuid4().hex,
                symbol=symbol,
                asset_class=infer_asset_class(symbol),
                requested_action="stop",
                mode_context=mode_context,
                requested_at_utc=utc_now_iso(),
                requested_from=requested_from,
                confirmation_state="not_required",
                outcome_state="blocked",
                outcome_message="Runtime is already stopped.",
                runtime_session_id="" if current_runtime is None else current_runtime.session_id,
            ),
        )

    result = stop_managed_runtime(
        config,
        symbol,
        registry_path=registry_file,
        terminate_process=terminate_process,
    )
    return _save_control_action(
        registry_file,
        config,
        ManagedControlAction(
            action_id=uuid4().hex,
            symbol=symbol,
            asset_class=infer_asset_class(symbol),
            requested_action="stop",
            mode_context=mode_context,
            requested_at_utc=utc_now_iso(),
            requested_from=requested_from,
            confirmation_state="not_required",
            outcome_state=_control_outcome_from_runtime_state(result.runtime_state),
            outcome_message=result.status_message,
            runtime_session_id=result.previous_session_id,
        ),
    )


def request_restart_runtime_action(
    config: BotConfig,
    symbol: str,
    *,
    mode: str | None = None,
    registry_path: Path | None = None,
    terminate_process: Any = _terminate_process,
    popen_factory: Any = subprocess.Popen,
    cwd: Path | None = None,
    python_executable: str | None = None,
    requested_from: str = "dashboard",
    confirmation_state: str = "not_required",
) -> ManagedControlAction:
    registry_file = Path(registry_path or config.runtime_registry_path)
    current_runtime = current_runtime_for_symbol(load_runtime_registry(registry_file), symbol)
    mode_context = _requested_mode_context(mode, config)
    if requested_from == "dashboard" and mode_context == "live" and confirmation_state != "confirmed":
        return _save_control_action(
            registry_file,
            config,
            ManagedControlAction(
                action_id=uuid4().hex,
                symbol=symbol,
                asset_class=infer_asset_class(symbol),
                requested_action="restart",
                mode_context=mode_context,
                requested_at_utc=utc_now_iso(),
                requested_from=requested_from,
                confirmation_state=confirmation_state,
                outcome_state="blocked",
                outcome_message=f"Live restart requires confirmation. Enter {config.live_confirmation_token} to continue.",
                runtime_session_id="" if current_runtime is None else current_runtime.session_id,
            ),
        )
    if current_runtime is not None and current_runtime.lifecycle_state in {"starting", "stopping", "restarting"}:
        return _save_control_action(
            registry_file,
            config,
            ManagedControlAction(
                action_id=uuid4().hex,
                symbol=symbol,
                asset_class=infer_asset_class(symbol),
                requested_action="restart",
                mode_context=mode_context,
                requested_at_utc=utc_now_iso(),
                requested_from=requested_from,
                confirmation_state=confirmation_state,
                outcome_state="blocked",
                outcome_message=f"Runtime is currently {current_runtime.lifecycle_state}.",
                runtime_session_id=current_runtime.session_id,
            ),
        )

    result = restart_managed_runtime(
        config,
        symbol,
        mode=mode_context,
        registry_path=registry_file,
        terminate_process=terminate_process,
        popen_factory=popen_factory,
        cwd=cwd,
        python_executable=python_executable,
    )
    return _save_control_action(
        registry_file,
        config,
        ManagedControlAction(
            action_id=uuid4().hex,
            symbol=symbol,
            asset_class=infer_asset_class(symbol),
            requested_action="restart",
            mode_context=mode_context,
            requested_at_utc=utc_now_iso(),
            requested_from=requested_from,
            confirmation_state=confirmation_state,
            outcome_state=_control_outcome_from_runtime_state(result.runtime_state),
            outcome_message=result.status_message,
            runtime_session_id=result.new_session_id,
        ),
    )
