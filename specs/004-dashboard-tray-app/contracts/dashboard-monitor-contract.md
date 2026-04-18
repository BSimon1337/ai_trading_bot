# Contract: Dashboard Monitor

## Purpose

Defines the operator-visible behavior and data contract for the local dashboard monitor.

## Dashboard Routes

### `GET /`

**Behavior**: Returns the human-facing dashboard view.

**Required content**:

- Application title and last refresh time
- One status card per monitored instance or symbol
- Current state label for each instance
- Latest action, reason, mode, and asset class
- Recent decision rows
- Recent fill rows
- Recent issue summary
- Clear no-data/warning messages for missing or malformed evidence

**Acceptance checks**:

- Does not crash when evidence files are missing.
- Does not expose credential values.
- Shows stale/blocked/failed states distinctly.
- Renders at least 10 monitored symbols or instances within the success criteria.

### `GET /health`

**Behavior**: Returns a machine-readable health response for the monitor process.

**Required fields**:

- `ok`: boolean
- `time_utc`: timestamp
- `monitor_state`: aggregate state
- `instances_count`: integer

**Acceptance checks**:

- Returns a successful response while the monitor is running.
- Does not require Alpaca network access.

### `GET /api/status`

**Behavior**: Returns the dashboard status model as structured data for tests, future UI refreshes, and tray aggregation.

**Required top-level fields**:

- `status_updated_utc`
- `aggregate_state`
- `instances`
- `issues`

**Instance fields**:

- `label`
- `status`
- `symbols`
- `latest_action`
- `latest_reason`
- `latest_mode`
- `latest_asset_class`
- `latest_update_utc`
- `heartbeat_age_minutes`
- `decisions_today`
- `fills_today`
- `recent_decisions`
- `recent_fills`
- `issues`

**Acceptance checks**:

- Uses existing runtime evidence files.
- Handles partial/malformed CSV files gracefully.
- Supports stock and slash-form crypto symbols.
- Never includes raw credential values.

## Refresh Behavior

- Browser view refreshes automatically.
- Structured status endpoint can be polled without restarting the monitor.
- Stale thresholds are visible in status output.

## Read-Only Guarantee

Dashboard routes in this feature are read-only. They must not place, approve, cancel, start, or stop trades.
