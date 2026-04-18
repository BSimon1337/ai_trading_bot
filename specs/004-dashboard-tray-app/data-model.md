# Data Model: Dashboard and Tray App

## Monitor Configuration

**Purpose**: Captures operator choices for the local monitor.

**Fields**:

- `dashboard_host`: host/interface used by the local dashboard
- `dashboard_port`: local dashboard port
- `refresh_seconds`: dashboard refresh interval
- `tray_enabled`: whether to attempt tray startup
- `read_only`: whether runtime controls are disabled
- `instances`: monitored dashboard instances

**Validation Rules**:

- `refresh_seconds` must be positive and should default to a safe low-friction value.
- `read_only` defaults to true.
- Secret credential values must not be included.
- Missing configuration falls back to existing dashboard/log defaults.

## Dashboard Instance

**Purpose**: Represents one monitored bot context, usually a symbol or configured log group.

**Fields**:

- `label`: operator-facing name
- `symbols`: associated symbols
- `asset_classes`: stock, crypto, system, or unknown values
- `decision_log_path`: decision evidence path
- `fill_log_path`: fill evidence path
- `snapshot_log_path`: daily snapshot evidence path
- `status`: derived runtime status
- `last_updated_at`: latest known evidence timestamp
- `latest_decision`: optional Decision Summary
- `latest_fill`: optional Fill Summary
- `latest_snapshot`: optional Snapshot Summary
- `issues`: recent Issue Summary items

**Validation Rules**:

- Missing paths produce no-data/warning status, not an exception.
- Malformed files produce warning status with an issue summary.
- Slash-form crypto symbols remain readable and must not break path/status formatting.

## Runtime Status

**Purpose**: Operator-facing health classification.

**Fields**:

- `state`: `running | paper | live | blocked | stale | failed | no_data | warning`
- `severity`: `ok | info | warning | critical`
- `message`: short operator-facing explanation
- `age_minutes`: minutes since latest evidence when known

**State Transitions**:

- No readable evidence -> `no_data`
- Recent paper evidence -> `paper`
- Recent active live evidence -> `live`
- Blocked-live event -> `blocked`
- Failed run event or broker rejection -> `failed` or `warning` depending severity
- Evidence older than freshness threshold -> `stale`

**Validation Rules**:

- Stale evidence must not be labeled healthy.
- Blocked live execution must retain the guardrail reason.

## Decision Summary

**Purpose**: Human-readable representation of a decision row.

**Fields**:

- `timestamp`
- `mode`
- `symbol`
- `asset_class`
- `action`
- `action_source`
- `model_prob_up`
- `sentiment_source`
- `sentiment_probability`
- `sentiment_label`
- `quantity`
- `portfolio_value`
- `cash`
- `reason`
- `result`

**Validation Rules**:

- Missing optional values display as blank or unavailable.
- Secret/config values are never included.
- Rows with guardrail, blocked, failed, or rejected reasons feed Issue Summary.

## Fill Summary

**Purpose**: Human-readable representation of an order/fill row.

**Fields**:

- `timestamp`
- `mode`
- `symbol`
- `asset_class`
- `side`
- `quantity`
- `order_id`
- `portfolio_value`
- `cash`
- `notional_usd`
- `result`

**Validation Rules**:

- Quantity may be fractional for crypto.
- Submitted, rejected, failed, and canceled results must remain distinguishable.

## Snapshot Summary

**Purpose**: Latest daily portfolio context for an instance.

**Fields**:

- `date`
- `mode`
- `symbol`
- `portfolio_value`
- `cash`
- `position_qty`
- `day_pnl`

**Validation Rules**:

- Numeric parsing failures display as unavailable and create a warning issue.
- Snapshot absence does not block decision/fill display.

## Issue Summary

**Purpose**: Condensed operator-visible warning/error.

**Fields**:

- `timestamp`
- `severity`
- `symbol`
- `category`
- `message`
- `source`

**Validation Rules**:

- Issues derive from runtime evidence only.
- Recent critical issues appear prominently in dashboard and tray state.

## Tray State

**Purpose**: Represents the desktop tray indicator.

**Fields**:

- `label`
- `state`
- `tooltip`
- `last_updated_at`
- `menu_actions`

**Validation Rules**:

- Must include Open Dashboard and Exit Monitor actions.
- Must degrade gracefully when tray support is unavailable.
- Must not expose credentials or raw config secrets.
