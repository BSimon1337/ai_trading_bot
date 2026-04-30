# Feature Specification: Monitor Runtime Observability

**Feature Branch**: `010-monitor-runtime-observability`  
**Created**: 2026-04-30  
**Status**: Draft  
**Input**: User description: "Capture the monitor/runtime gaps so symbol cards stay consistent, runtime truth matches actual bot behavior, and the dashboard shows the important live events, warnings, and provisional-versus-confirmed state without making the operator guess."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Runtime Truth From The Dashboard (Priority: P1)

An operator can look at the dashboard and trust that each symbol card reflects the real runtime state of the managed bot instead of a stale or incomplete approximation.

**Why this priority**: If the dashboard can say a bot is running when it is dead, or stopped when it is trading, the rest of the monitor loses credibility.

**Independent Test**: Can be fully tested by starting, stopping, restarting, and intentionally interrupting one managed stock bot and one managed crypto bot, then confirming the dashboard state matches the actual runtime state without checking terminal output.

**Acceptance Scenarios**:

1. **Given** a managed bot is running, **When** the operator refreshes the dashboard, **Then** the card shows the current runtime state and mode context that match the active managed runtime.
2. **Given** a managed bot exits unexpectedly after launch, **When** the dashboard refreshes, **Then** the card no longer presents the bot as healthy running state and instead shows the reconciled failed or stopped state.
3. **Given** a managed bot has been intentionally stopped, **When** older trading evidence still exists, **Then** the card shows the bot as stopped and does not present stale historical evidence as if it were current runtime health.

---

### User Story 2 - Understand What The Bot Just Did (Priority: P2)

An operator can see the important recent runtime and order-lifecycle events for each symbol without tailing terminal logs.

**Why this priority**: Runtime control only feels complete when the operator can also see what happened after the click, including warnings, fills, and whether the bot made it through startup.

**Independent Test**: Can be fully tested by launching a bot, letting it initialize, waiting for one or more trading iterations, and verifying the dashboard shows recent runtime milestones, broker warnings, and order-lifecycle progress for that symbol.

**Acceptance Scenarios**:

1. **Given** a managed bot starts successfully, **When** the operator views its dashboard card, **Then** the recent runtime view shows startup and readiness activity in human-readable order.
2. **Given** an order progresses through submission and fill events, **When** the operator views the symbol card, **Then** the dashboard shows the latest order-lifecycle status instead of only the final action label.
3. **Given** the broker or runtime emits a symbol-specific warning, **When** the dashboard refreshes, **Then** that warning is visible on the relevant symbol card without requiring terminal access.

---

### User Story 3 - See Consistent Portfolio State Across Symbols (Priority: P3)

An operator can compare stock and crypto cards side by side and see the same meaning from the same fields, even when one symbol is waiting on a snapshot and another just filled a trade.

**Why this priority**: Mixed symbol sets should not feel like different products, and the current paper/live, running/live, and zero-held-after-fill inconsistencies are confusing.

**Independent Test**: Can be fully tested by running a mixed stock-and-crypto dashboard, forcing fresh fills and snapshot lag, and confirming that the cards stay visually and semantically consistent.

**Acceptance Scenarios**:

1. **Given** a fresh filled order is newer than the latest portfolio snapshot, **When** the operator views the symbol card, **Then** the card shows a clearly labeled provisional position state instead of a misleading zero position.
2. **Given** two symbols share the same runtime mode and state, **When** the operator compares their cards, **Then** both cards use the same badge semantics and state wording regardless of asset type.
3. **Given** a symbol has no recent headlines or no fills yet, **When** the operator views the card, **Then** the card distinguishes "not yet available" from "error" and from "stale historical data."
4. **Given** multiple symbols are running with different holdings or value states, **When** the dashboard refreshes after startup activity, **Then** one symbol's held value or cash state is not copied or leaked into another symbol's card.

---

### Edge Cases

- What happens when a bot starts successfully but has not yet written its first decision row or first snapshot row?
- How does the dashboard behave when a broker warning is emitted without a matching fill or decision row?
- What happens when a symbol has fresh fill evidence but delayed or malformed snapshot evidence?
- How does the system present runtime state when a managed child process exits between dashboard refreshes?
- What happens when one symbol has current runtime activity while another symbol only has historical evidence from an older session?
- What happens when the dashboard looked correct before startup, but symbol values become duplicated or overwritten after the runtime state switches to active?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST reconcile dashboard runtime state against current managed runtime truth so symbols are not shown as healthy running when their managed process is no longer active.
- **FR-002**: The dashboard MUST present running, starting, restarting, stopping, stopped, and failed states consistently across stock and crypto symbols.
- **FR-003**: The dashboard MUST show the effective trading mode context for every managed symbol in a way that does not fall back to ambiguous generic wording when live or paper context is already known.
- **FR-004**: The dashboard MUST expose recent runtime activity for each symbol, including startup progress and other operator-relevant lifecycle milestones.
- **FR-005**: The dashboard MUST expose recent order-lifecycle state for each symbol in a form that lets the operator distinguish submission, pending, fill, rejection, and no-order states.
- **FR-006**: The dashboard MUST surface symbol-specific broker or runtime warnings in the symbol view instead of leaving them only in terminal output.
- **FR-007**: The system MUST distinguish current confirmed portfolio state from provisional portfolio state when fresh fills are newer than the latest portfolio snapshot.
- **FR-008**: When the dashboard shows provisional portfolio data, it MUST label that state clearly enough that an operator can tell it is derived from fresher evidence than the latest snapshot.
- **FR-009**: The dashboard MUST use the same field semantics, wording, and badge meanings for stock and crypto symbols when the underlying state is equivalent.
- **FR-010**: The system MUST differentiate between unavailable, stale, historical, provisional, and failed data conditions so operators are not forced to infer whether a field is empty because nothing happened, because evidence is delayed, or because something is wrong.
- **FR-011**: The dashboard MUST continue to reuse the existing runtime registry and runtime evidence flows instead of requiring a separate operator-only data entry path.
- **FR-012**: The system MUST preserve existing monitor and runtime-manager safety behavior while improving observability, including for live-managed bots.
- **FR-013**: The dashboard MUST keep each symbol's portfolio values, held quantity, held value, and cash state isolated to that symbol so one symbol's evidence cannot overwrite or masquerade as another symbol's state during or after runtime startup.
- **FR-014**: The dashboard MUST preserve correct symbol state when a runtime transitions from pre-start or idle evidence into fresh active runtime evidence, without regressing previously correct values into duplicated or mismatched values.

### Key Entities *(include if feature involves data)*

- **Runtime Event Entry**: A monitor-visible summary of a managed bot lifecycle event, including symbol, event time, runtime phase, mode context, and operator-facing description.
- **Order Lifecycle Entry**: A monitor-visible summary of the latest order state for a symbol, including lifecycle phase, action direction, time, and whether the state is final or still in progress.
- **Warning Event**: A symbol-scoped broker, runtime, or evidence warning that should be visible in the dashboard, including severity, origin, time, and human-readable message.
- **Effective Portfolio State**: The operator-facing position, cash, and held-value view for a symbol, including whether the values come from confirmed snapshot evidence or fresher provisional fill evidence.
- **Evidence Freshness State**: The classification that explains whether the displayed data is current, stale, historical, unavailable, or provisional.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: The current Flask monitor in [tradingbot/app/monitor.py](/c:/Users/Beau/ai_trading_bot/tradingbot/app/monitor.py), the dashboard template in [templates/monitor.html](/c:/Users/Beau/ai_trading_bot/templates/monitor.html), the runtime registry and managed lifecycle flow in [tradingbot/app/runtime_manager.py](/c:/Users/Beau/ai_trading_bot/tradingbot/app/runtime_manager.py), the tray entrypoints, and the existing symbol-scoped CSV runtime evidence files.
- **Planned deviations**: The monitor will move further from a passive summary view toward a richer operator observability surface, but it will still reuse the current registry-and-evidence architecture instead of introducing a separate backend service.
- **New dependencies**: None.
- **Operational impact**: Expands monitor-visible runtime detail, warning visibility, order-lifecycle visibility, and freshness labeling for live and paper workflows across both stock and crypto symbols.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In validation scenarios covering at least one stock symbol and one crypto symbol, the dashboard runtime state matches actual managed process state for at least 95% of refreshes following start, stop, restart, and unexpected exit events.
- **SC-002**: After a fresh fill occurs before the next portfolio snapshot, the dashboard shows a clearly labeled non-misleading provisional position state on the next refresh instead of a false zero-held state.
- **SC-003**: Operators can identify whether a symbol is live or paper, healthy or failed, and provisional or confirmed without consulting terminal logs in 100% of tested mixed-symbol workflows.
- **SC-004**: Symbol-specific warnings that affect runtime interpretation appear in the dashboard within one monitor refresh cycle in at least 95% of tested warning scenarios.
- **SC-005**: In operator walkthrough testing, a user can explain the latest runtime outcome and latest trade lifecycle state for a symbol in under 30 seconds using only the dashboard.
- **SC-006**: In mixed-symbol validation runs, no symbol card shows another symbol's held value, cash value, or other portfolio state after managed runtimes are started and refreshed.

## Assumptions

- The existing runtime registry and symbol-scoped CSV evidence files remain the primary observability inputs for this phase.
- This feature focuses on making current runtime behavior visible and trustworthy rather than replacing terminal logs with a full developer-grade log console.
- The monitor continues to be used by a trusted local operator and does not need multi-user event attribution in this phase.
- Stock and crypto symbols will continue sharing one dashboard surface, so consistency of wording and state semantics is more important than asset-specific presentation differences.
