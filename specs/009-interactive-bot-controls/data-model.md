# Data Model: Interactive Bot Controls

## Managed Control Action

**Purpose**: Represents one operator-requested lifecycle action submitted from the dashboard.

**Fields**:

- `action_id`
- `symbol`
- `asset_class`
- `requested_action`
- `mode_context`
- `requested_at_utc`
- `requested_from`
- `confirmation_state`
- `outcome_state`
- `outcome_message`
- `runtime_session_id`

**Validation Rules**:

- `requested_action` must be one of `start`, `stop`, or `restart`.
- `mode_context` must distinguish `paper` from `live`.
- `confirmation_state` must distinguish actions that are not yet confirmed from actions that are confirmed or do not require extra confirmation.
- `outcome_state` must distinguish `pending`, `succeeded`, `failed`, and `blocked`.

## Control Availability State

**Purpose**: Represents what actions are currently allowed for a managed symbol.

**Fields**:

- `symbol`
- `asset_class`
- `runtime_state`
- `can_start`
- `can_stop`
- `can_restart`
- `availability_message`
- `requires_live_confirmation`

**Validation Rules**:

- Availability must be derived from current managed runtime state rather than trading-log freshness alone.
- A running symbol cannot be shown as startable at the same time unless a restart-only recovery case is explicitly represented.
- Live confirmation requirements must be visible before execution, not only after submission.

## Control Activity Entry

**Purpose**: Represents a recent control action shown back to the operator after execution.

**Fields**:

- `action_id`
- `timestamp_utc`
- `symbol`
- `asset_class`
- `mode_context`
- `requested_action`
- `outcome_state`
- `outcome_message`
- `session_id`

**Validation Rules**:

- Entries must be bounded so history stays readable.
- Recent activity must remain readable for both stock and crypto symbols in one shared list.
- Entries must not expose credentials or secret values.

## Dashboard Control Session

**Purpose**: Represents a short-lived UI confirmation context for an action that needs explicit operator approval before execution.

**Fields**:

- `symbol`
- `requested_action`
- `mode_context`
- `confirmation_prompt`
- `expires_at_utc`

**Validation Rules**:

- Live confirmations must expire if not completed.
- A confirmation session must not outlive the operator-visible prompt that created it.
- Paper actions may skip this entity when confirmation is not required.

## Runtime Registry Extension

**Purpose**: Extends the existing runtime registry so dashboard control features can be reconstructed on refresh.

**Fields**:

- `managed_runtimes`
- `recent_sessions`
- `recent_control_actions`
- `updated_at_utc`

**Validation Rules**:

- Current runtime state remains authoritative over recent control history.
- Recent control actions must never replace the current runtime entry for a symbol.
- Registry updates from control actions must remain readable even if a requested action fails.
