# Contract: Monitor Runtime Integration

## Purpose

Defines the runtime-manager fields that the existing dashboard and tray monitor must expose once the app owns bot lifecycle state.

## `GET /api/status`

**Behavior**: Returns the current dashboard status model with runtime-manager state merged into each symbol instance.

**Required new instance fields**:

- `runtime_state`
- `runtime_status_message`
- `runtime_session_id`
- `runtime_pid`
- `runtime_started_at_utc`
- `runtime_last_seen_utc`
- `last_lifecycle_event`
- `is_fresh_runtime_session`

**Acceptance checks**:

- Running, stopped, restarting, failed, and paused states are distinguishable.
- A fresh restarted runtime is shown as current even if older sessions for the same symbol failed.
- A symbol with no active runtime is shown as stopped rather than silently absent.
- Runtime-manager state must be readable even when decision/fill CSV evidence is quiet or historical.

## `GET /`

**Behavior**: Returns the operator-facing dashboard with runtime-manager lifecycle clarity integrated into each symbol card and detail view.

**Required content**:

- visible runtime state per symbol
- readable last lifecycle event or status message
- indication of whether the current runtime session is fresh
- continued display of the existing decision/fill/snapshot observability
- clear distinction between `stopped` and `stale` so operators do not confuse a deliberate stop with a dead or quiet bot

**Acceptance checks**:

- Operators can tell from the dashboard whether a symbol is truly running or only has stale trading logs.
- Runtime-manager state does not replace or hide current trading evidence; it complements it.

## Tray Behavior

**Behavior**: Tray summary reflects aggregate runtime-manager state alongside current monitor health.

**Required tray signals**:

- number of running managed symbols
- any failed managed symbol runtimes
- latest runtime-manager refresh time

**Acceptance checks**:

- Tray can distinguish “monitor alive but bot stopped” from “bot actively running.”
- Runtime-manager state remains read-only unless a later feature explicitly adds interactive controls.
