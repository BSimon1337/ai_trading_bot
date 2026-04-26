# Data Model: Monitor Accuracy Refinement

## Account Summary Snapshot

**Purpose**: Represents the one authoritative account-level summary shown by the monitor for the current refresh cycle.

**Fields**:

- `source_instance_label`
- `source_timestamp`
- `cash`
- `account_equity`
- `day_pnl`
- `instances_count`
- `instances_with_fills`
- `is_stale`

**Validation Rules**:

- Must come from one freshest trusted source per refresh cycle.
- Must not be created by summing per-symbol account values.
- If all candidate sources are stale or malformed, summary remains readable but flagged accordingly.

## Instance Activity Summary

**Purpose**: Represents the trusted current operational state of one monitored bot instance.

**Fields**:

- `label`
- `symbols`
- `status_state`
- `status_severity`
- `latest_update_utc`
- `heartbeat_age_minutes`
- `latest_action`
- `latest_reason`
- `last_decision_time`
- `last_fill_time`
- `broker_rejection_count`
- `position_qty`
- `held_value`
- `cash_context`
- `issues`
- `notes`

**Validation Rules**:

- Latest valid evidence must outweigh older failures once a newer healthy restart exists.
- Broker rejections raise warning context but do not by themselves mark the instance inactive if fresh evidence continues.
- Missing optional timing fields must display as unavailable rather than erroring.

## Value Evidence

**Purpose**: Represents the inputs that can support a held-value estimate for a symbol.

**Fields**:

- `symbol`
- `position_qty`
- `valuation_timestamp`
- `valuation_source`
- `unit_value`
- `is_trusted`

**Validation Rules**:

- Held value may only be derived when quantity and a trusted unit value are both available.
- Fill-derived price is valid when recent and internally consistent.
- If no trusted valuation exists, held value should remain unavailable rather than defaulting to zero.

## Issue Entry

**Purpose**: Represents an actionable current operator problem.

**Fields**:

- `timestamp`
- `instance_label`
- `symbol`
- `severity`
- `category`
- `message`
- `source`
- `is_current`

**Validation Rules**:

- Current issues must be tied to active evidence or the active evidence window.
- Historical issues may remain viewable but must not override current healthy status.
- Informational conditions must not be stored as issues.

## Informational Note

**Purpose**: Represents useful but non-actionable operator context.

**Fields**:

- `timestamp`
- `instance_label`
- `symbol`
- `category`
- `message`
- `source`

**Validation Rules**:

- Notes must not change instance severity to warning or critical.
- Notes should remain readable and distinct from issues.

## Retention Window

**Purpose**: Defines what evidence counts as active for status classification.

**Fields**:

- `window_name`
- `active_start_time`
- `active_end_time`
- `archived_paths`
- `ignored_paths`
- `reason`

**Validation Rules**:

- Active monitoring must prefer evidence inside the active window.
- Archived or ignored evidence remains available for manual review but not active state override.
- Rotation behavior must not hide all evidence for a currently running bot.
