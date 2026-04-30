# Contract: Dashboard Runtime Events

## Purpose

Defines the operator-facing event and warning behavior required for each symbol card so the dashboard can explain runtime progress, trade lifecycle, and symbol-specific anomalies without relying on terminal output.

## Per-Symbol Runtime Event Feed

**Behavior**: Each symbol card exposes a bounded recent event list summarizing the most important runtime milestones for that symbol.

**Required fields per event**:

- `event_id`
- `timestamp_utc`
- `runtime_phase`
- `mode_context`
- `event_source`
- `summary`
- `runtime_session_id`

**Acceptance checks**:

- A successful dashboard-issued start produces visible startup and ready-state evidence in the event list.
- A restarted runtime shows a fresh session context instead of reusing the prior session's event identity.
- An unexpectedly exited runtime produces a visible failed or exited event within the next monitor refresh cycle.
- Runtime event summaries remain symbol-scoped and do not cause another symbol's runtime or value state to be reused during startup-heavy refreshes.

## Per-Symbol Warning Surface

**Behavior**: Each symbol card surfaces active operator-relevant warnings tied to that symbol.

**Required fields per warning**:

- `warning_id`
- `severity`
- `warning_type`
- `origin`
- `timestamp_utc`
- `message`
- `is_active`

**Acceptance checks**:

- A broker or runtime warning appears on the relevant symbol card without appearing on unrelated symbols.
- A malformed evidence warning remains distinguishable from a broker rejection or runtime failure.
- Warning wording is concise enough for dashboard use and does not expose secrets.

## Order Lifecycle Summary

**Behavior**: Each symbol card surfaces the latest order-lifecycle understanding instead of only the final action label.

**Required fields**:

- `action_side`
- `lifecycle_state`
- `lifecycle_source`
- `event_time_utc`
- `is_terminal`
- `display_summary`

**Acceptance checks**:

- Submitted, pending, filled, rejected, canceled, and no-order states remain distinguishable.
- A recent fill is visible even when the next portfolio snapshot has not yet landed.
- A symbol with no recent order state does not inherit another symbol's lifecycle state.
