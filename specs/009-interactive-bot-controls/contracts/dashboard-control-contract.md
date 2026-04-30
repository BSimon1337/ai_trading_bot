# Contract: Dashboard Control Actions

## Purpose

Defines how the local dashboard requests start, stop, and restart actions for managed runtimes and what operator-visible result each action must return for both stock and crypto symbols.

## `POST /control/start`

**Behavior**: Requests that the app start a managed runtime for one symbol.

**Required request inputs**:

- `symbol`
- `mode_context`
- `asset_class`
- live confirmation input when required

**Required result fields**:

- `symbol`
- `requested_action`
- `outcome_state`
- `outcome_message`
- `confirmation_state`
- `runtime_session_id` when launch succeeds

**Acceptance checks**:

- A start request for a stopped symbol creates a readable pending or running result path.
- A start request for an already-running symbol returns a non-destructive blocked or no-op explanation.
- Live start requests remain blocked unless the required confirmation step succeeds.
- Stock and crypto symbols use the same action contract, even if their later trading behavior differs.

## `POST /control/stop`

**Behavior**: Requests that the app stop the currently managed runtime for one symbol.

**Required request inputs**:

- `symbol`

**Required result fields**:

- `symbol`
- `requested_action`
- `outcome_state`
- `outcome_message`
- `confirmation_state`
- `previous_session_id` when available

**Acceptance checks**:

- Stopping a running symbol results in a readable stopped or stopping outcome.
- Stopping a symbol that is already stopped does not crash and returns a clear operator-visible explanation.

## `POST /control/restart`

**Behavior**: Requests that the app replace the current runtime for one symbol with a fresh managed session.

**Required request inputs**:

- `symbol`
- `mode_context`
- `asset_class`
- live confirmation input when required

**Required result fields**:

- `symbol`
- `requested_action`
- `outcome_state`
- `outcome_message`
- `confirmation_state`
- `old_session_id` when available
- `new_session_id` when restart succeeds

**Acceptance checks**:

- Restart creates a fresh session identity on success.
- A failed restart returns a clear reason without falsely presenting the old session as freshly restarted.
- Live restart remains subject to the same confirmation and safeguard expectations as live start.
- Operator-visible wording must distinguish paper and live restart intent before execution.

## Recent Control Activity

**Behavior**: Each completed or blocked dashboard-issued control action is retained in recent activity for later operator review.

**Required result fields**:

- `action_id`
- `timestamp_utc`
- `symbol`
- `asset_class`
- `mode_context`
- `requested_action`
- `requested_from`
- `confirmation_state`
- `outcome_state`
- `outcome_message`
- `runtime_session_id`

**Acceptance checks**:

- Recent activity can show both stock and crypto actions together.
- Recent activity remains readable after page refresh.
- No secrets or confirmation tokens are exposed in activity entries.
- Blocked actions must still appear with an explanation so operators can reconstruct what happened.
