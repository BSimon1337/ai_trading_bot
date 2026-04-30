# Data Model: Monitor Runtime Observability

## Symbol Observability View

**Purpose**: Represents the complete operator-facing state for one symbol card after runtime, evidence, warnings, and freshness have been reconciled.

**Fields**:

- `symbol`
- `asset_class`
- `mode_context`
- `runtime_state`
- `runtime_session_id`
- `status_badge`
- `effective_portfolio_state`
- `latest_order_lifecycle`
- `recent_runtime_events`
- `active_warnings`
- `freshness_state`
- `historical_issue_count`

**Validation Rules**:

- The view must be derived independently per symbol.
- Runtime state must prefer reconciled managed runtime truth over stale historical evidence.
- Equivalent stock and crypto states must produce equivalent badge semantics and field meanings.

## Runtime Event Entry

**Purpose**: Represents one recent operator-relevant runtime milestone for a symbol.

**Fields**:

- `event_id`
- `symbol`
- `timestamp_utc`
- `mode_context`
- `runtime_phase`
- `event_source`
- `summary`
- `session_id`

**Validation Rules**:

- Entries must remain symbol-scoped.
- Entries must be ordered newest-first or otherwise consistently ordered in the UI.
- Entries must summarize source conditions without exposing secrets or requiring terminal-only context.

## Order Lifecycle Entry

**Purpose**: Represents the latest order-progress understanding for a symbol.

**Fields**:

- `symbol`
- `action_side`
- `lifecycle_state`
- `lifecycle_source`
- `event_time_utc`
- `is_terminal`
- `broker_order_id`
- `display_summary`

**Validation Rules**:

- Lifecycle state must distinguish submission from fill, rejection, cancellation, and no-order states.
- The entry must not imply a fill when only a submission or pending state is known.
- The lifecycle view must remain readable even when the source evidence is partial.

## Warning Event

**Purpose**: Represents a symbol-scoped or system-scoped warning that changes how an operator should interpret current state.

**Fields**:

- `warning_id`
- `symbol`
- `severity`
- `warning_type`
- `origin`
- `timestamp_utc`
- `message`
- `is_active`

**Validation Rules**:

- Warnings must distinguish broker/runtime issues from stale or malformed evidence issues.
- A warning must remain tied to the relevant symbol unless it is truly system-scoped.
- Warning wording must be operator-readable and not require raw log parsing.

## Effective Portfolio State

**Purpose**: Represents the per-symbol held quantity, held value, and related cash context shown on the dashboard.

**Fields**:

- `symbol`
- `position_qty`
- `held_value`
- `cash`
- `portfolio_value`
- `value_source`
- `snapshot_timestamp_utc`
- `fill_timestamp_utc`
- `is_provisional`

**Validation Rules**:

- The state must be derived only from evidence belonging to the same symbol.
- `is_provisional` must be true when a fresher fill is being used ahead of the latest valid snapshot.
- The view must never reuse another symbol's values as fallback state.

## Evidence Freshness State

**Purpose**: Represents how current and trustworthy the displayed evidence is for a symbol.

**Fields**:

- `symbol`
- `freshness_label`
- `decision_freshness`
- `fill_freshness`
- `snapshot_freshness`
- `runtime_freshness`
- `explanation`

**Validation Rules**:

- Freshness labels must distinguish `current`, `provisional`, `stale`, `historical`, and `unavailable`.
- The explanation must make it clear whether the limitation is due to delay, absence, or failure.
- Freshness state must not override runtime truth; it only explains evidence quality.
