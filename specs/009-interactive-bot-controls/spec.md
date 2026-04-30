# Feature Specification: Interactive Bot Controls

**Feature Branch**: `009-interactive-bot-controls`  
**Created**: 2026-04-28  
**Status**: Draft  
**Input**: User description: "Interactive dashboard controls for starting, stopping, and restarting bots, while keeping both stock trading and crypto trading in scope."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Control One Managed Bot From The Dashboard (Priority: P1)

An operator can start, stop, or restart a single managed trading bot directly from the dashboard without dropping into PowerShell, and can do so for either a stock symbol or a crypto symbol.

**Why this priority**: This delivers the main usability gain from the runtime-manager work and turns the monitor into an actual operator console.

**Independent Test**: Can be fully tested by opening the dashboard, issuing start/stop/restart actions for one stock symbol and one crypto symbol, and confirming runtime state changes without using CLI commands.

**Acceptance Scenarios**:

1. **Given** a managed symbol is stopped, **When** the operator starts it from the dashboard, **Then** the bot enters a visible startup state and later shows the current managed runtime state for that symbol.
2. **Given** a managed symbol is running, **When** the operator stops it from the dashboard, **Then** the bot stops and the dashboard shows a stopped state instead of stale or failed log-derived status.
3. **Given** a managed symbol is running, **When** the operator restarts it from the dashboard, **Then** the prior session is replaced by a fresh managed session and the dashboard shows the new session identity.

---

### User Story 2 - Safely Confirm Live Control Actions (Priority: P2)

An operator can clearly distinguish paper and live control actions, receives explicit confirmation messaging before live-impacting actions, and can understand why an action is blocked when safeguards are not satisfied.

**Why this priority**: Interactive controls are only trustworthy if they preserve the live-trading safety posture already established in the app.

**Independent Test**: Can be fully tested by attempting live and paper control actions from the dashboard and confirming the app requires the right confirmation flow, preserves safeguards, and reports blocked actions clearly.

**Acceptance Scenarios**:

1. **Given** the operator is about to start or restart a live runtime, **When** the action is initiated from the dashboard, **Then** the interface presents a clear live-mode confirmation before the action is executed.
2. **Given** a requested runtime action violates an existing safeguard, **When** the operator submits the action, **Then** the action is not executed and the dashboard shows a clear reason.
3. **Given** a paper runtime action is requested, **When** the operator confirms it, **Then** the action proceeds without being mislabeled as live.

---

### User Story 3 - See Recent Control Activity And Coverage Across Asset Types (Priority: P3)

An operator can review recent dashboard-issued control actions, understand whether they were applied successfully, and manage a mixed set of stock and crypto symbols without the controls feeling crypto-only.

**Why this priority**: The app needs to feel coherent and auditable once we move control into the UI, especially because the user wants stock capability preserved alongside crypto.

**Independent Test**: Can be fully tested by managing a mixed stock-and-crypto symbol set from the dashboard and confirming recent actions, outcomes, and asset coverage are visible without checking terminal output.

**Acceptance Scenarios**:

1. **Given** the operator has recently controlled one stock symbol and one crypto symbol, **When** the dashboard refreshes, **Then** recent control activity shows both actions with their outcome and timing.
2. **Given** a symbol is managed by the runtime manager but has quiet trading logs, **When** the operator views the dashboard, **Then** control affordances still appear based on managed runtime coverage rather than recent trades alone.

---

### Edge Cases

- What happens when the operator clicks start for a symbol that is already running?
- How does the system behave when a runtime exits during or immediately after a dashboard-issued action?
- What happens when the operator controls a symbol whose runtime registry entry exists but whose prior log evidence is stale?
- How does the system behave when both stock and crypto symbols are configured, but only one asset type currently has active runtimes?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard MUST let an operator start, stop, and restart any symbol currently managed by the runtime manager.
- **FR-002**: The dashboard MUST support interactive controls for both stock symbols and crypto symbols without requiring separate operator workflows.
- **FR-003**: The system MUST show current action availability per symbol so the operator can tell whether start, stop, or restart is currently applicable.
- **FR-004**: The system MUST preserve the existing runtime-manager safeguards for live and paper operation when actions are initiated from the dashboard.
- **FR-005**: The system MUST require an explicit live-action confirmation step before executing a dashboard-issued live start or live restart.
- **FR-006**: The system MUST reject control actions that violate runtime or live-trading safeguards and MUST present a clear operator-visible reason for the rejection.
- **FR-007**: The system MUST show action progress and final outcome in the dashboard without requiring the operator to inspect terminal output.
- **FR-008**: The system MUST record recent dashboard-issued control actions with symbol, requested action, mode context, time, and outcome.
- **FR-009**: The system MUST keep the monitor’s runtime state as the source of truth for whether a symbol is running, stopped, restarting, failed, paused, or stale after a control action.
- **FR-010**: The system MUST keep control behavior compatible with mixed symbol sets so that adding or managing stock symbols does not reduce current crypto control capability, and vice versa.
- **FR-011**: The system MUST continue to operate when trading evidence is quiet by using managed runtime state to determine whether control affordances should be shown.
- **FR-012**: The system MUST present control-related messaging in a way that distinguishes paper actions from live actions at the moment the operator decides what to do.

### Key Entities *(include if feature involves data)*

- **Managed Control Action**: An operator-requested runtime command for a symbol, including requested action type, asset context, mode context, request time, completion state, and operator-visible result.
- **Control Availability State**: The currently allowed control actions for a symbol based on managed runtime state, safeguards, and whether the symbol is a stock or crypto runtime.
- **Control Activity Entry**: A recent-action record that summarizes what was requested, for which symbol, when it was requested, and whether it succeeded, failed, or was blocked.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: The current Flask monitor/dashboard, runtime manager lifecycle commands, runtime registry, tray visibility patterns, and existing stock/crypto symbol parsing and runtime flows.
- **Planned deviations**: The monitor will no longer remain purely read-only; it will become an operator console for runtime lifecycle actions while preserving existing safeguards.
- **New dependencies**: None.
- **Operational impact**: Adds dashboard-issued runtime actions, recent control activity, confirmation messaging for live mode, and operator-visible control state across both stock and crypto managed symbols.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can start, stop, or restart a managed symbol from the dashboard without using terminal commands.
- **SC-002**: In validation scenarios covering at least one stock symbol and one crypto symbol, dashboard-issued control actions show the correct outcome and resulting runtime state for at least 95% of attempts on first try.
- **SC-003**: Operators can distinguish whether a control action is paper or live before execution in 100% of tested dashboard control flows.
- **SC-004**: When a dashboard-issued action is blocked by safeguards, the operator sees a clear reason within the same control flow without needing terminal logs.
- **SC-005**: Recent control activity remains understandable enough that an operator can identify the latest action, target symbol, and outcome for mixed stock/crypto workflows in under 30 seconds.

## Assumptions

- Existing managed runtime flows remain the backend execution path for start, stop, and restart actions.
- Initial interactive controls focus on runtime lifecycle actions rather than full strategy-setting edits.
- The operator is a trusted local user of the app and does not require multi-user permission modeling in this phase.
- Stock trading capability remains part of the product scope even if current day-to-day testing is more crypto-heavy.
