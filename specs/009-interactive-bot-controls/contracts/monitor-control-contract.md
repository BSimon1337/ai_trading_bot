# Contract: Monitor Interactive Control Integration

## Purpose

Defines the dashboard payload and page behavior required to expose runtime lifecycle controls safely and clearly across both stock and crypto managed symbols.

## `GET /api/status`

**Behavior**: Returns the current dashboard status model with interactive-control state merged into each managed symbol instance.

**Required new instance fields**:

- `control_asset_class`
- `control_mode_context`
- `control_runtime_state`
- `can_start`
- `can_stop`
- `can_restart`
- `control_availability_message`
- `requires_live_confirmation`

**Required top-level fields**:

- `recent_control_actions`
- `latest_control_updated_at_utc`

**Acceptance checks**:

- Control availability is derived even when trading logs are quiet.
- Both stock and crypto symbols expose the same core action fields.
- Runtime truth remains authoritative when a recent control action conflicts with stale trading evidence.
- Asset-class-specific labels may differ, but the operator should not need to learn a separate control workflow.

## `GET /`

**Behavior**: Returns the operator-facing dashboard with visible lifecycle controls and recent control activity.

**Required content**:

- per-symbol start, stop, and restart affordances
- visible distinction between paper and live action context
- live confirmation prompt when required
- recent control activity showing action, symbol, time, and outcome
- continued visibility of current runtime state and trading evidence

**Acceptance checks**:

- Operators can manage a stopped stock symbol and a stopped crypto symbol from the same dashboard flow.
- Operators can tell whether a requested action was applied, blocked, or failed without opening a terminal.
- Live actions are clearly labeled before execution.
- Quiet or stopped stock symbols must remain controllable even when the monitor has no fresh trading decisions to show.

## Tray Behavior

**Behavior**: Tray remains read-focused in this feature while reflecting the latest control-related runtime outcomes.

**Required tray signals**:

- current aggregate runtime state counts
- latest runtime refresh time
- visibility of failed runtime outcomes after dashboard-issued actions

**Acceptance checks**:

- Tray remains consistent with dashboard runtime state after an action is taken.
- Tray does not become the primary action surface in this feature phase.
