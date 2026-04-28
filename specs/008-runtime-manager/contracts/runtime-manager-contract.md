# Contract: Runtime Manager

## Purpose

Defines the local application-owned interface for starting, stopping, restarting, and reading managed symbol runtimes.

## Start Runtime

**Behavior**: Starts one managed symbol runtime using the existing bot entrypoint and symbol-scoped log-path conventions.

**Required request inputs**:

- `symbol`
- `mode`
- `log_path_scope`
- `live_safety_context`

**Required result fields**:

- `symbol`
- `session_id`
- `runtime_state`
- `started_at_utc`
- `pid` or launch failure explanation
- `status_message`

**Acceptance checks**:

- A successful start creates or updates the managed runtime record for that symbol.
- A failed start returns a readable failure reason without leaving a false running state.
- Live-mode starts respect existing explicit live-safety expectations.

## Stop Runtime

**Behavior**: Stops the currently managed runtime for one symbol.

**Required request inputs**:

- `symbol`

**Required result fields**:

- `symbol`
- `previous_session_id`
- `runtime_state`
- `stopped_at_utc`
- `status_message`

**Acceptance checks**:

- Stopping a running symbol marks it stopped or failed with a clear reason.
- Stopping an already-dead symbol resolves cleanly without crashing.

## Restart Runtime

**Behavior**: Replaces the current managed runtime for one symbol with a fresh session.

**Required request inputs**:

- `symbol`
- `mode`
- `live_safety_context`

**Required result fields**:

- `symbol`
- `old_session_id`
- `new_session_id`
- `runtime_state`
- `started_at_utc`
- `status_message`

**Acceptance checks**:

- Restart creates a new session identity.
- Old session state does not remain displayed as the current runtime after a successful restart.
- Live restart remains subject to existing live-safety expectations.

## Runtime Registry Read

**Behavior**: Returns the current managed runtime registry for monitor and tray consumption.

**Required result fields**:

- `updated_at_utc`
- `managed_runtimes`
- `recent_sessions`
- `registry_version`

**Acceptance checks**:

- Registry can be read even when some symbol runtimes are stopped.
- Per-symbol state remains independent.
- No credentials or secrets appear in runtime-manager payloads.
- One symbol must never expose more than one authoritative current runtime entry at the same time.
