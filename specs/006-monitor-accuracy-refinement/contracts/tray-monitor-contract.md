# Contract: Tray Monitor Accuracy Refinement

## Purpose

Defines how the tray monitor reflects refined status, issues, and activity clarity from the dashboard data model.

## Tray State Inputs

The tray must derive its state from the refined dashboard status model and respect:

- current aggregate state
- count of current actionable issues
- count of informational notes
- latest update time
- monitored instance count

## Required Tray Behaviors

### Aggregate State

- `running`: current instances are healthy or active without actionable issues
- `warning`: one or more current actionable warning issues exist, but no current critical failure dominates
- `critical`: a current blocked or failed state exists in the active evidence window
- `unavailable`: tray support is unavailable while dashboard-only monitoring remains usable

### Tooltip or Summary Text

Must expose:

- aggregate state
- monitored instance count
- current actionable issue count
- latest update time when available

### Menu Actions

- `Open Dashboard`
- `Refresh Status`
- `Exit Monitor`

## Acceptance Checks

- Older failed evidence does not keep the tray in a critical state after a newer healthy restart is recognized.
- Informational notes do not count as warning or critical issues.
- Refresh rereads current dashboard status without mutating trading behavior.
- Exit Monitor stops only the monitor process owned by the launcher.

## Safety Contract

The tray remains read-only for trading and must not place orders, approve live trading, cancel orders, or alter safeguards.
