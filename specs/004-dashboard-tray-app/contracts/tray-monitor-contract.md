# Contract: Tray Monitor

## Purpose

Defines the desktop tray behavior for the local monitor.

## Startup

**Inputs**:

- Monitor configuration
- Dashboard URL
- Read-only mode setting

**Expected behavior**:

- Starts or attaches to the local dashboard monitor.
- Creates a tray item on supported desktop environments.
- Shows a clear application label such as "AI Trading Bot Monitor".
- Exposes status without requiring the operator to type into a terminal.

## Tray State

**Required state values**:

- `running`: monitor is healthy
- `warning`: monitor is running but one or more instances have warnings/stale/no-data
- `critical`: blocked/failed state detected
- `unavailable`: tray support is unavailable, while browser dashboard remains usable

**Required display data**:

- Tooltip or label with aggregate state
- Last update time when available
- Count of monitored instances when available

## Menu Actions

### Open Dashboard

**Behavior**: Opens the local dashboard URL or brings the dashboard view to the foreground when supported.

**Acceptance checks**:

- Works without exposing credentials in command arguments or logs.
- Leaves bot trading processes untouched.

### Refresh Status

**Behavior**: Re-reads monitor status and updates tray text/icon state.

**Acceptance checks**:

- Does not require Alpaca network access.
- Does not mutate trading state.

### Exit Monitor

**Behavior**: Exits the tray monitor and dashboard monitor process owned by this launcher.

**Acceptance checks**:

- Cleans up tray resources.
- Does not kill separate trading bot processes unless future explicit process-control requirements are added.

## Degraded Mode

If tray initialization fails, the monitor must:

- Keep the browser dashboard available when possible.
- Emit an operator-readable warning.
- Exit cleanly if no dashboard or tray can be started.

## Safety Contract

The tray monitor is read-only for trading. It must not place orders, approve live trading, cancel orders, or modify live-trading safeguards.
