# Feature Specification: Monitor Accuracy Refinement

**Feature Branch**: `006-monitor-accuracy-refinement`  
**Created**: 2026-04-25  
**Status**: Draft  
**Input**: User description: "Refine the local trading monitor for accuracy and operator clarity. The dashboard must separate true issues from informational notes, show correct account-level summary metrics from a single authoritative source, display per-asset held value reliably even when recent fills are missing, add clearer per-bot activity timestamps and broker rejection counts, and prevent stale or historical failures from overriding the current live status after a successful restart. The system should also define a safe log retention or rotation approach so old malformed or failed runs do not pollute the current monitor view. Reuse the existing Flask/template monitor, tray, CSV evidence, and modular Python patterns."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trust Current Monitor Status (Priority: P1)

As the bot operator, I want each monitored instance to show trustworthy current status and account metrics so I can tell whether the bot is truly live, what cash and equity are available, and whether a symbol is active without cross-checking terminal logs or broker pages.

**Why this priority**: If the dashboard cannot be trusted as the current source of truth, every other monitor improvement loses value and the operator must fall back to manual verification.

**Independent Test**: Can be tested by running the monitor against fixture and live-like evidence where bots have restarted, filled orders, or remained idle, then confirming the dashboard shows current status, current account summary values, and does not mark a healthy restarted bot as failed because of older evidence.

**Acceptance Scenarios**:

1. **Given** a bot instance has a historical failed run followed by a newer successful restart, **When** the operator opens the dashboard, **Then** the instance shows its current live or paper state instead of remaining failed because of the older event.
2. **Given** multiple monitored crypto instances share the same trading account, **When** the operator views the dashboard, **Then** the account summary shows one authoritative set of current cash, equity, and day PnL values rather than conflicting per-card totals.
3. **Given** a symbol has current holdings but no recent fill record, **When** the operator views that symbol card, **Then** the dashboard still shows a reliable held-value estimate instead of zero or blank unless no trustworthy valuation input exists.

---

### User Story 2 - Read Problems and Activity Quickly (Priority: P2)

As the bot operator, I want the monitor to separate real problems from normal informational notes and show clearer bot activity timing so I can quickly tell what needs attention versus what is merely informative.

**Why this priority**: The current monitor is useful, but mixing informational notes with actionable issues slows down diagnosis and creates uncertainty during live trading.

**Independent Test**: Can be tested by loading evidence with warnings, informational notes, recent fills, broker rejections, and idle-but-healthy bots, then confirming the dashboard groups them clearly and exposes last decision time, last fill time, and rejection counts for each bot.

**Acceptance Scenarios**:

1. **Given** the latest monitor evidence includes negative day PnL but no operational problem, **When** the operator views recent activity, **Then** that information appears as a note rather than as a warning or critical issue.
2. **Given** a bot has not traded recently but is still evaluating normally, **When** the operator views the bot card, **Then** the card shows its last decision time and last fill time so the operator can distinguish idle behavior from a stalled process.
3. **Given** a bot receives repeated broker rejections, **When** the operator views the monitor, **Then** the dashboard shows a rejection count and keeps the bot visible as running unless a newer critical failure actually stops it.

---

### User Story 3 - Keep Old Evidence from Polluting Current Monitoring (Priority: P3)

As the bot operator, I want the monitor to manage stale or malformed historical evidence safely so that old failed runs, malformed CSV rows, or leftover runtime files do not distort the current view of active bots.

**Why this priority**: Historical evidence is valuable for debugging, but it should not overpower the current operational picture or repeatedly create false alarms after a clean restart.

**Independent Test**: Can be tested by mixing current evidence with older malformed, failed, and archived runtime files and confirming the monitor preserves useful history while keeping the current status and issue list focused on active evidence.

**Acceptance Scenarios**:

1. **Given** old runtime evidence exists from prior failed or malformed runs, **When** the operator restarts the monitor and active bots, **Then** the monitor emphasizes current evidence and does not keep showing stale critical states as current failures.
2. **Given** old runtime files are rotated or archived according to the defined retention approach, **When** the operator views the monitor, **Then** current dashboards remain clean while older evidence remains available for manual investigation.
3. **Given** a malformed historical file is still present, **When** the monitor refreshes, **Then** it reports the problem in a bounded, readable way without crashing or obscuring current healthy instances.

### Edge Cases

- A symbol can hold an asset with no recent fill record in the current log set but still needs a trustworthy held-value estimate.
- Multiple symbol-specific processes can share one underlying account while writing separate evidence files at different times.
- A bot can restart cleanly after a failed or blocked run, and the monitor must prefer the latest valid state rather than the most alarming older state.
- Log rotation or archiving must not hide all evidence for a currently running bot.
- Historical malformed files may still exist on disk and must not crash the monitor or permanently contaminate current status.
- Informational conditions such as small negative day PnL or neutral sentiment should not be elevated into actionable issues unless they cross a defined operational threshold.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST derive account-level summary metrics from one authoritative current source per refresh cycle so cash, equity, and day PnL remain internally consistent across the monitor.
- **FR-002**: System MUST display per-asset held quantity and held-value estimates for each monitored symbol when sufficient trustworthy evidence exists.
- **FR-003**: System MUST prefer the most recent valid runtime evidence for status classification and MUST NOT allow older failed or blocked events to override a newer healthy restart.
- **FR-004**: System MUST separate operator-facing issues from informational notes in the monitor view.
- **FR-005**: System MUST show per-bot last decision time, last fill time, and broker rejection count when that evidence is available.
- **FR-006**: System MUST keep bots visible as currently running when they are still producing current evidence, even if recent broker rejections occurred.
- **FR-007**: System MUST keep historical and malformed evidence from polluting the active monitor view by applying a defined retention, rotation, or archival approach.
- **FR-008**: System MUST preserve read-only monitoring behavior and MUST NOT place, approve, cancel, or otherwise control trades.
- **FR-009**: System MUST continue handling missing, empty, malformed, or partially written evidence files gracefully without crashing.
- **FR-010**: System MUST reuse existing monitor, tray, CSV evidence, and modular application patterns unless a documented deviation is required.

### Key Entities *(include if feature involves data)*

- **Account Summary Snapshot**: The monitor’s authoritative current account-level view, including cash, equity, day PnL, source instance, and last update time.
- **Instance Activity Summary**: The latest trusted operational summary for one monitored bot instance, including current state, last decision time, last fill time, rejection count, and latest evidence age.
- **Issue Entry**: A current operator-facing problem that needs attention, such as blocked execution, stale evidence, malformed active evidence, or repeated broker rejection behavior.
- **Informational Note**: A non-critical monitor message that adds context without representing an operational failure, such as slight negative day PnL or an idle-but-healthy hold cycle.
- **Retention Window**: The bounded set of runtime evidence considered active for status classification, separate from archived or older historical evidence retained for manual review.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: The existing Flask dashboard and API monitor flow, tray monitor flow, CSV evidence readers, runtime logging outputs, template-based dashboard rendering, and modular app/config patterns already present in the repository.
- **Planned deviations**: No new UI stack or control plane is planned. The refinement stays within the current local monitor architecture and tightens interpretation, grouping, and evidence-handling behavior.
- **New dependencies**: None expected.
- **Operational impact**: The monitor will show clearer current-versus-historical status, cleaner issue grouping, more trustworthy account and asset values, and a defined approach for handling old runtime evidence so live monitoring remains readable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In validation scenarios with mixed historical and current evidence, 100% of restarted healthy bots display their current live or paper status instead of a stale failed state.
- **SC-002**: Operators can identify current account cash, equity, and latest bot activity times for all monitored instances within 15 seconds of opening the dashboard.
- **SC-003**: In monitor validation scenarios, informational notes and actionable issues are classified correctly in 100% of acceptance tests.
- **SC-004**: For symbols with current holdings and enough valuation evidence, held-value displays are populated correctly in 100% of validation tests.
- **SC-005**: Historical malformed or failed evidence no longer causes current healthy instances to appear failed in validation scenarios after a successful restart.
- **SC-006**: The monitor continues to refresh and render without crashing in 100% of tests that include missing, archived, malformed, or mixed-age evidence files.

## Assumptions

- The monitor remains a local operator tool rather than a hosted multi-user service.
- The same existing evidence sources remain the basis for monitor truth, with refinement focused on interpretation and presentation rather than replacing the data source entirely.
- A single refresh cycle can determine one authoritative account summary source even when multiple instances write account-related evidence at different times.
- Historical evidence should remain available for manual debugging even if it is no longer treated as active status input.
- Trade controls, order approvals, and live-guardrail changes remain out of scope for this refinement feature.
