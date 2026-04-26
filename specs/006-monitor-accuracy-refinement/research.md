# Research: Monitor Accuracy Refinement

## Decision: Use One Freshest Trusted Account Snapshot per Refresh

**Decision**: Derive one authoritative account summary for each monitor refresh from the freshest valid account-related evidence row, then present that summary once in the dashboard rather than treating each symbol card as a separate account total.

**Rationale**: Multiple symbol-specific processes can write account context at slightly different times. Selecting one freshest trusted source per refresh keeps cash, equity, and day PnL internally consistent and avoids conflicting totals across cards.

**Alternatives considered**:

- **Repeat account values independently on every symbol card**: Rejected because it makes the monitor look inconsistent when timestamps differ by a few seconds.
- **Aggregate account totals by summing per-symbol evidence**: Rejected because those values are already account-wide in the evidence and would double-count.
- **Query the broker directly for current account state**: Rejected for this refinement because the monitor intentionally stays read-only and local-evidence-based.

## Decision: Held Value Falls Back Through Trusted Evidence Sources

**Decision**: Estimate per-asset held value using the best available trusted evidence in this order: current position quantity plus latest trustworthy valuation input for that symbol, with recent fill-derived price as one allowed source but not the only one.

**Rationale**: Symbols can hold assets without a recent fill in the current log window, especially after restart or rotation. A fallback chain avoids displaying `$0.00` for a real position while still refusing to invent a value when no trustworthy source exists.

**Alternatives considered**:

- **Use recent fill price only**: Rejected because it fails after restarts, retention cleanup, or older holdings with no recent fill.
- **Show blank whenever a recent fill is missing**: Rejected because operators still need a useful held-value estimate for active positions.
- **Add external market-quote fetching to the monitor**: Rejected for now because it adds network dependency and changes the evidence model.

## Decision: Separate Issues from Informational Notes

**Decision**: Split monitor output into actionable issues and informational notes, keeping operational problems prominent while moving non-actionable context such as slight negative day PnL into a softer note stream.

**Rationale**: Operators need to tell the difference between “needs attention” and “good to know” at a glance. Combining them slows diagnosis and creates false urgency.

**Alternatives considered**:

- **Keep one mixed recent issues list**: Rejected because informational messages dilute the value of true warnings and critical alerts.
- **Suppress informational context entirely**: Rejected because operators still benefit from non-critical context such as negative day PnL or recent idle behavior.

## Decision: Current State Must Be Newer Than Historical Failures

**Decision**: Status classification will favor the latest valid runtime evidence and treat older failed or blocked events as historical once a newer healthy restart or current heartbeat exists for the same instance.

**Rationale**: The most harmful monitor inaccuracy observed was a healthy restarted bot still showing as failed because of older evidence in the same log set. State aging and restart precedence must be explicit.

**Alternatives considered**:

- **Always surface the most severe recent event**: Rejected because it lets stale failures override current truth.
- **Ignore historical failures completely**: Rejected because operators still need them in history, just not as the active state.

## Decision: Use Safe Log Retention or Archival Instead of Deletion-Heavy Cleanup

**Decision**: Define a safe retention approach that keeps current monitoring focused on an active evidence window while allowing older malformed or failed files to be archived or ignored for active status purposes rather than deleted aggressively.

**Rationale**: Historical runtime evidence still matters for debugging, but active monitoring should not be polluted by old runs. A safe archival/rotation model keeps both goals compatible.

**Alternatives considered**:

- **Delete old logs automatically**: Rejected because it destroys debugging evidence and can be risky around active runtime files.
- **Treat every historical file as active forever**: Rejected because it causes stale failures and malformed rows to keep contaminating the current view.

## Decision: Rejection Counts and Activity Timestamps Belong in Instance Summaries

**Decision**: Track per-instance last decision time, last fill time, and broker rejection count directly in the instance summary payload used by both dashboard and tray status.

**Rationale**: These values let the operator distinguish healthy-but-idle bots from stalled bots and recognize repeated broker friction without digging into raw CSV files.

**Alternatives considered**:

- **Leave the operator to infer activity from raw tables**: Rejected because it slows diagnosis and undermines the monitor’s purpose.
- **Show only latest action/reason**: Rejected because it hides whether the bot has actually been evaluating recently or filling trades.
## Confirmation: Refinement Stayed Read-Only and Dependency-Neutral

**Decision**: Keep the refinement inside the existing monitor, tray, and template modules without adding broker polling, trade controls, or new dependencies.

**Rationale**: This feature is about trust, clarity, and safe evidence handling. Adding control behavior or new packages would expand risk without helping the core operator problem.

**Validation outcome**:

- No new Python packages were introduced.
- `tradingbot/app/tray.py` still opens the dashboard, refreshes monitor state, and exits the tray only.
- The monitor remains evidence-driven and read-only.
