# Contract: Dashboard Monitor Accuracy Refinement

## Purpose

Defines the refined operator-facing behavior for the local dashboard monitor.

## `GET /api/status`

**Behavior**: Returns the current dashboard status model as structured data suitable for the browser dashboard, tray aggregation, and tests.

**Required top-level fields**:

- `status_updated_utc`
- `aggregate_state`
- `account_overview`
- `instances`
- `issues`
- `notes`
- `recent_activity_rows`

**Required `account_overview` fields**:

- `cash`
- `account_equity`
- `day_pnl`
- `source_instance`
- `latest_update_utc`
- `instances_count`
- `instances_with_fills`
- `is_stale`

**Required instance fields**:

- `label`
- `status`
- `latest_action`
- `latest_reason`
- `latest_update_utc`
- `last_decision_utc`
- `last_fill_utc`
- `broker_rejection_count`
- `position_qty`
- `held_value`
- `held_value_source`
- `cash`
- `account_equity`
- `issues`
- `notes`
- `heartbeat_age_minutes`

**Acceptance checks**:

- Current healthy evidence overrides older failed evidence for the same instance.
- Account overview is internally consistent and sourced from one authoritative current evidence row.
- Held value remains populated when a trusted fallback valuation source exists even if no recent fill exists.
- Issues and notes are returned separately.
- Malformed, missing, archived, or historical evidence does not crash the response.
- No credential values appear anywhere in the payload.

## `GET /`

**Behavior**: Returns the human-facing dashboard with the refined operator view.

**Required content**:

- Account overview shown once
- Distinct issues section
- Distinct informational notes section
- Recent decisions or activity table that continues to reflect active evidence rows
- Per-instance cards with current status, held quantity, held value, cash context, last decision time, last fill time, and rejection count
- Clear indication when evidence is historical, stale, or unavailable

**Acceptance checks**:

- A healthy restarted bot does not remain visually failed because of older evidence.
- Informational notes do not appear styled as actionable issues.
- Per-instance cards remain readable when some evidence types are missing.

## Historical Evidence Handling

- Current status classification must use only the active evidence window.
- Historical malformed or failed files may appear as bounded historical context, but not as the active state for a newly healthy instance.
- Retention or archival handling must keep current dashboards readable without deleting all debugging history.
- Historical evidence may still appear in manual inspection workflows, but the primary dashboard state and account overview must be derived from current evidence only.

## Read-Only Guarantee

This refinement remains strictly read-only. The dashboard must not place trades, approve trades, cancel orders, or change bot runtime state.
