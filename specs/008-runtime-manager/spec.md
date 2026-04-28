# Feature Specification: Runtime Manager

**Feature Branch**: `008-runtime-manager`  
**Created**: 2026-04-26  
**Status**: Draft  
**Input**: User description: "Turn the bot into a more full-fledged local application by replacing the manual multi-PowerShell workflow with an app-owned runtime manager that can start, stop, restart, and track per-symbol bot processes safely."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start And Track Bot Processes From One Place (Priority: P1)

As the bot operator, I want the application to start and track per-symbol bot processes from one shared runtime layer so I do not have to manually manage multiple PowerShell windows just to run the system.

**Why this priority**: The current manual process workflow is the biggest structural weakness in the app. Without a runtime manager, the monitor can observe the system but the application still cannot own it.

**Independent Test**: Can be tested by starting a configured set of paper or live symbol runtimes through the runtime manager and confirming the application records per-symbol running state, process ownership, and launch evidence without relying on manual shell tracking.

**Acceptance Scenarios**:

1. **Given** configured symbols are available and no runtime is active, **When** the operator starts one symbol through the application runtime layer, **Then** the symbol process launches and the application records it as running with its symbol-specific state and log paths.
2. **Given** multiple symbols are configured, **When** the operator starts more than one symbol, **Then** the application tracks each symbol process independently rather than treating them as one shared unnamed runtime.
3. **Given** a symbol runtime exits unexpectedly, **When** the application refreshes runtime state, **Then** the monitor shows that symbol as stopped or failed instead of incorrectly showing it as still running.

---

### User Story 2 - Stop, Restart, And Protect Live Runtime Actions (Priority: P2)

As the bot operator, I want the application to stop or restart bot processes safely so I can recover from lockouts, stale sessions, or bad launches without killing Python processes blindly or accidentally changing live behavior without clear confirmation.

**Why this priority**: Once the app owns runtime state, safe lifecycle control is the next highest-value step. This removes the operational friction that currently comes from hand-managed process restarts.

**Independent Test**: Can be tested by stopping and restarting paper and live runtimes through the runtime manager, confirming state transitions are reflected in the monitor and that live-mode actions remain guarded and explicit.

**Acceptance Scenarios**:

1. **Given** a symbol runtime is currently running, **When** the operator stops that symbol through the runtime layer, **Then** the process is terminated cleanly and the application marks it as stopped.
2. **Given** a symbol runtime is running in a bad or paused state, **When** the operator restarts that symbol through the runtime layer, **Then** the old process is replaced by a fresh one and the new runtime is tracked as a new active session.
3. **Given** live trading is enabled for a symbol, **When** the operator attempts a live runtime start or restart, **Then** the application applies the existing live-safety expectations rather than silently bypassing them.

---

### User Story 3 - Keep Runtime State Explainable In The Monitor (Priority: P3)

As the bot operator, I want the monitor to show runtime-manager state clearly so I can tell which symbols are running, paused, stopped, failed, or recently restarted without reading raw process lists or guessing from stale log timestamps.

**Why this priority**: The monitor is already the operator’s main dashboard. Once the application owns runtime state, that state needs to become first-class and understandable there.

**Independent Test**: Can be tested by exercising start, stop, restart, and failure scenarios and confirming the dashboard reflects runtime-manager state, process freshness, and operator-visible explanations without losing the existing read-focused monitor value.

**Acceptance Scenarios**:

1. **Given** the runtime manager is tracking active and inactive symbol processes, **When** the operator views the monitor, **Then** each symbol shows its current runtime-manager state and the last known lifecycle event.
2. **Given** a symbol was restarted recently, **When** the operator views the monitor, **Then** the monitor shows that it is a fresh runtime and does not let stale prior failures dominate the current state.
3. **Given** no runtime is active for a configured symbol, **When** the operator views the monitor, **Then** the dashboard clearly shows it as stopped rather than merely missing or stale.

### Edge Cases

- A configured symbol may already have a manually started bot process outside the runtime manager, and the application must not misidentify or duplicate ownership silently.
- A start request can fail because configuration, dependencies, or credentials are invalid, and the runtime manager must surface that failure clearly without leaving ghost running state.
- A stop request can target a runtime that already exited unexpectedly, and the application must resolve that cleanly without hanging on stale process identifiers.
- Multiple symbols can share the same underlying account while using separate processes, so runtime status must stay per-symbol even when account-level monitor values are shared.
- Live-mode start or restart actions must remain explicit and must not accidentally bypass current live-trading safety expectations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide an application-owned runtime manager that tracks bot runtimes per symbol.
- **FR-002**: System MUST allow a symbol runtime to be started from a shared runtime-manager entrypoint rather than requiring manual shell-only management.
- **FR-003**: System MUST allow a tracked symbol runtime to be stopped cleanly through the runtime manager.
- **FR-004**: System MUST allow a tracked symbol runtime to be restarted through the runtime manager.
- **FR-005**: System MUST record runtime-manager state per symbol, including whether a symbol is running, stopped, restarting, failed, or paused.
- **FR-006**: System MUST record enough runtime evidence to identify the process or session currently associated with each managed symbol.
- **FR-007**: System MUST surface runtime-manager state to the existing dashboard and tray monitor in an operator-readable form.
- **FR-008**: System MUST keep symbol ownership independent so multiple symbol processes can run concurrently without collapsing into one shared runtime state.
- **FR-009**: System MUST distinguish between a runtime that is intentionally stopped and one that failed unexpectedly.
- **FR-010**: System MUST integrate with the existing live-trading safeguards for live starts and restarts rather than introducing an unguarded control path.
- **FR-011**: System MUST preserve existing symbol-specific log path behavior so runtime-manager launched bots still write monitor evidence in a symbol-scoped way.
- **FR-012**: System MUST tolerate missing, dead, or stale tracked processes gracefully without crashing the app or leaving permanently incorrect running state.
- **FR-013**: System MUST reuse the existing modular app, monitor, strategy, and configuration patterns where practical rather than creating a parallel control architecture.
- **FR-014**: System MUST keep the monitor’s data-reading behavior compatible with existing CSV evidence while adding runtime-manager state visibility.

### Key Entities *(include if feature involves data)*

- **Managed Runtime**: The application-owned representation of a bot process for one symbol, including symbol identity, current lifecycle state, and associated runtime metadata.
- **Runtime Session**: A single launch instance of a managed runtime, including start time, stop time, session freshness, and failure or stop reason.
- **Runtime Registry**: The current set of managed symbol runtimes known to the application at refresh time.
- **Lifecycle Event**: An operator-visible start, stop, restart, failure, or pause event associated with a managed runtime.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: `tradingbot/app/main.py`, `tradingbot/app/live.py`, `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, `tradingbot/config/settings.py`, the existing symbol-specific CSV evidence layout, and the current live-safety configuration patterns.
- **Planned deviations**: The current manual external-shell workflow will no longer be the primary runtime-management path. A dedicated runtime-manager layer will become the app’s authoritative process owner.
- **New dependencies**: None assumed for the initial runtime-manager feature unless the planning phase proves a small process-management helper is necessary.
- **Operational impact**: Bot launch, stop, and restart behavior will move under application control; the monitor will gain runtime-manager lifecycle visibility; manual PowerShell management will become optional rather than required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can start a configured symbol runtime through the application and see it reflected in monitor state within 10 seconds without opening a separate manual process-management shell.
- **SC-002**: In validation scenarios with multiple configured symbols, 100% of active symbol runtimes are tracked independently with correct current lifecycle state.
- **SC-003**: In validation scenarios where a managed runtime is stopped or restarted, the monitor reflects the new runtime state within one refresh cycle and does not continue showing the prior session as active.
- **SC-004**: In validation scenarios where a managed runtime exits unexpectedly, the application detects and surfaces the failure without crashing and without leaving a false running state behind.
- **SC-005**: Live-mode runtime actions continue to honor explicit live-safety expectations in 100% of tested live-start and live-restart scenarios.

## Assumptions

- The current per-symbol bot design remains in place, so the runtime manager will orchestrate multiple single-symbol runtimes rather than collapsing them into one multi-symbol Lumibot live process.
- Existing monitor CSV evidence remains the main observability source for strategy activity, while the runtime manager adds process and lifecycle state on top.
- The initial runtime-manager feature will focus on local single-machine operation rather than remote orchestration or multi-user control.
- Existing configuration patterns and environment-backed settings remain the source of runtime launch inputs until a later settings-management feature formalizes interactive configuration editing.
- Full interactive dashboard controls may be implemented later, but this feature’s core purpose is establishing the authoritative backend runtime layer first.
