# Data Model: Runtime Manager

## Managed Runtime

**Purpose**: Represents the application-owned current runtime state for one symbol.

**Fields**:

- `symbol`
- `instance_label`
- `mode`
- `lifecycle_state`
- `session_id`
- `pid`
- `started_at_utc`
- `last_seen_utc`
- `stop_requested_at_utc`
- `last_exit_code`
- `failure_reason`
- `decision_log_path`
- `fill_log_path`
- `snapshot_log_path`

**Validation Rules**:

- One managed runtime record exists per symbol.
- `lifecycle_state` must be one of `starting`, `running`, `stopping`, `stopped`, `restarting`, `failed`, or `paused`.
- `pid` must be blank when the runtime is not currently running.
- Log paths must remain symbol-scoped and aligned with the managed symbol.

## Runtime Session

**Purpose**: Represents one concrete launch attempt for a managed runtime.

**Fields**:

- `session_id`
- `symbol`
- `mode`
- `launch_command`
- `launch_env_scope`
- `started_at_utc`
- `ended_at_utc`
- `exit_code`
- `end_reason`
- `was_live_mode`
- `was_manual_recovery`

**Validation Rules**:

- Each restart creates a new session.
- A session may be active or completed, but not both.
- `end_reason` must distinguish operator stop, guarded stop, crash, and launch failure.

## Runtime Registry

**Purpose**: Represents the full local set of managed runtimes known to the application.

**Fields**:

- `registry_version`
- `updated_at_utc`
- `managed_runtimes`
- `recent_sessions`

**Validation Rules**:

- Registry writes must preserve one authoritative current runtime entry per symbol.
- Registry must stay readable even when some symbol runtimes are stopped.
- Historical sessions may be bounded, but current runtime state must always remain present.

## Lifecycle Event

**Purpose**: Represents an operator-visible start, stop, restart, pause, or failure transition.

**Fields**:

- `timestamp_utc`
- `symbol`
- `session_id`
- `event_type`
- `message`
- `source`

**Validation Rules**:

- Events must be readable by the monitor without requiring raw process inspection.
- `event_type` must support at least `start_requested`, `running`, `stop_requested`, `stopped`, `restart_requested`, `restarted`, `failed`, and `paused`.

## Monitor Runtime View

**Purpose**: Represents the runtime-manager-specific portion of what the dashboard shows for a symbol.

**Fields**:

- `symbol`
- `runtime_state`
- `runtime_status_message`
- `session_id`
- `pid`
- `last_lifecycle_event`
- `started_at_utc`
- `last_seen_utc`
- `is_fresh_session`

**Validation Rules**:

- Current runtime-manager state must outweigh stale older sessions for the same symbol.
- A stopped runtime must be distinguishable from missing evidence.
- Runtime state must remain visible even when decision/fill activity is temporarily quiet.
