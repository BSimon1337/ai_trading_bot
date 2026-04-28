# Tasks: Runtime Manager

**Input**: Design documents from `/specs/008-runtime-manager/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the plan requires pytest unit, contract, and smoke validation for runtime registry behavior, lifecycle transitions, monitor payload shaping, and launch-path safety.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Prepare the runtime-manager feature scaffolding and document the app-owned lifecycle boundary.

- [x] T001 Document the runtime-manager scope, reused app surfaces, and operational evidence path in `specs/008-runtime-manager/plan.md`
- [x] T002 [P] Refresh runtime-manager fixture and validation guidance in `specs/008-runtime-manager/quickstart.md`
- [x] T003 [P] Review and tighten the runtime-manager interface expectations in `specs/008-runtime-manager/contracts/runtime-manager-contract.md` and `specs/008-runtime-manager/contracts/monitor-runtime-contract.md`

---

## Phase 2: Foundational

**Purpose**: Establish the shared runtime registry, lifecycle models, and monitor integration seam before story-specific lifecycle controls begin.

**Critical**: No user story work should start until the runtime-manager state model and monitor wiring points are in place.

- [x] T004 Implement managed runtime, runtime session, and runtime registry dataclasses in `tradingbot/app/runtime_manager.py`
- [x] T005 Implement local runtime-registry load/save helpers and bounded recent-session handling in `tradingbot/app/runtime_manager.py`
- [x] T006 [P] Add runtime-manager configuration fields and defaults for registry/state paths in `tradingbot/config/settings.py`
- [x] T007 [P] Add foundational unit tests for runtime-registry serialization and state transitions in `tests/unit/test_runtime_manager.py`
- [x] T008 [P] Add runtime-manager monitor fixture builders and sample registry evidence in `tests/fixtures/monitor/build_fixtures.py`
- [x] T009 Add monitor-side registry loading and base runtime-state merge helpers in `tradingbot/app/monitor.py`
- [x] T010 [P] Add foundational monitor payload tests for runtime-state parsing in `tests/unit/test_monitor_data.py`

**Checkpoint**: Shared runtime-manager state and monitor integration primitives are ready for lifecycle features.

---

## Phase 3: User Story 1 - Start And Track Bot Processes From One Place (Priority: P1) 🎯 MVP

**Goal**: Let the application launch one managed runtime per symbol and track its current process/session state.

**Independent Test**: Start one or more symbol runtimes through the runtime manager and confirm the app records per-symbol running state, session identity, and symbol-scoped evidence ownership without relying on manual shell tracking.

### Tests for User Story 1

- [ ] T011 [P] [US1] Add unit tests for managed runtime creation and running-state registration in `tests/unit/test_runtime_manager.py`
- [ ] T012 [P] [US1] Add unit tests for symbol-scoped log-path derivation and session identity handling in `tests/unit/test_runtime_manager.py`
- [ ] T013 [P] [US1] Add monitor contract tests for required runtime-state fields on instances in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T014 [P] [US1] Add smoke coverage for starting one managed symbol runtime in `tests/smoke/test_runtime_manager_entrypoint.py`

### Implementation for User Story 1

- [ ] T015 [US1] Implement symbol-scoped launch command and environment assembly in `tradingbot/app/runtime_manager.py`
- [ ] T016 [US1] Implement runtime start and current-session registration flow in `tradingbot/app/runtime_manager.py`
- [ ] T017 [US1] Add a runtime-manager entrypoint and startup hook in `tradingbot/app/main.py`
- [ ] T018 [US1] Surface managed runtime state, session id, pid, and lifecycle timestamps in `tradingbot/app/monitor.py`
- [ ] T019 [US1] Update per-symbol dashboard rendering for runtime state visibility in `templates/monitor.html`
- [ ] T020 [US1] Validate User Story 1 by running `tests/unit/test_runtime_manager.py`, `tests/unit/test_monitor_data.py`, `tests/contract/test_dashboard_monitor_contract.py`, and `tests/smoke/test_runtime_manager_entrypoint.py`

**Checkpoint**: The application can start and track managed symbol runtimes from one shared backend layer.

---

## Phase 4: User Story 2 - Stop, Restart, And Protect Live Runtime Actions (Priority: P2)

**Goal**: Let the application stop and restart tracked runtimes safely while preserving current live-safety expectations.

**Independent Test**: Stop and restart managed paper and live runtimes through the runtime manager, then confirm state transitions are tracked correctly and live safety remains explicit.

### Tests for User Story 2

- [ ] T021 [P] [US2] Add unit tests for stop-request and graceful stopped-state handling in `tests/unit/test_runtime_manager.py`
- [ ] T022 [P] [US2] Add unit tests for restart session replacement and fresh-session precedence in `tests/unit/test_runtime_manager.py`
- [ ] T023 [P] [US2] Add unit tests for live-safety gating during runtime start and restart in `tests/unit/test_runtime_manager.py`
- [ ] T024 [P] [US2] Add smoke coverage for stop and restart flows in `tests/smoke/test_runtime_manager_entrypoint.py`

### Implementation for User Story 2

- [ ] T025 [US2] Implement runtime stop flow and dead-process reconciliation in `tradingbot/app/runtime_manager.py`
- [ ] T026 [US2] Implement runtime restart flow with new session creation in `tradingbot/app/runtime_manager.py`
- [ ] T027 [US2] Integrate existing live-safety expectations into runtime-manager launch and restart paths in `tradingbot/app/runtime_manager.py` and `tradingbot/config/settings.py`
- [ ] T028 [US2] Expose stop/restart lifecycle events and stop/failure reasons to the monitor payload in `tradingbot/app/monitor.py`
- [ ] T029 [US2] Update tray runtime summary to reflect managed runtime failures and running counts in `tradingbot/app/tray.py`
- [ ] T030 [US2] Validate User Story 2 by running `tests/unit/test_runtime_manager.py`, `tests/contract/test_tray_monitor_contract.py`, `tests/contract/test_dashboard_monitor_contract.py`, and `tests/smoke/test_runtime_manager_entrypoint.py`

**Checkpoint**: Operators can stop or restart managed runtimes safely without blind process killing or live-safety regressions.

---

## Phase 5: User Story 3 - Keep Runtime State Explainable In The Monitor (Priority: P3)

**Goal**: Make runtime-manager state first-class in the dashboard and tray so operators can tell what is running, stopped, failed, or freshly restarted.

**Independent Test**: Exercise start, stop, restart, and failure scenarios and confirm the monitor clearly distinguishes current runtime state from stale trading logs.

### Tests for User Story 3

- [ ] T031 [P] [US3] Add unit tests for stopped-versus-stale runtime interpretation in `tests/unit/test_monitor_data.py`
- [ ] T032 [P] [US3] Add contract tests for runtime-manager monitor fields and fresh-session behavior in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T033 [P] [US3] Add tray contract coverage for aggregate runtime-state signaling in `tests/contract/test_tray_monitor_contract.py`

### Implementation for User Story 3

- [ ] T034 [US3] Add runtime-state classification helpers and stale-session precedence rules in `tradingbot/app/monitor.py`
- [ ] T035 [US3] Update dashboard cards and detail sections to show runtime state, last lifecycle event, and fresh-session context in `templates/monitor.html`
- [ ] T036 [US3] Update tray text and aggregate-state behavior for runtime-manager visibility in `tradingbot/app/tray.py`
- [ ] T037 [US3] Validate User Story 3 by running `tests/unit/test_monitor_data.py`, `tests/contract/test_dashboard_monitor_contract.py`, `tests/contract/test_tray_monitor_contract.py`, and `tests/smoke/test_monitor_entrypoint.py`

**Checkpoint**: The monitor can explain managed runtime state clearly instead of leaving operators to infer it from stale evidence.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, operator guidance, and end-to-end runtime-manager validation.

- [ ] T038 [P] Review runtime-state field naming and lifecycle wording for consistency across `tradingbot/app/runtime_manager.py`, `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, and `templates/monitor.html`
- [ ] T039 [P] Update operator-facing runtime-manager guidance in `README.md` and `specs/008-runtime-manager/quickstart.md`
- [ ] T040 [P] Confirm no new unsafe control path or credential exposure was introduced in `specs/008-runtime-manager/research.md`, `tradingbot/app/runtime_manager.py`, and `tradingbot/app/monitor.py`
- [ ] T041 Run full runtime-manager validation from `specs/008-runtime-manager/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational and builds on the managed runtime/session infrastructure from US1
- **User Story 3 (Phase 5)**: Depends on Foundational and benefits from the lifecycle events and runtime-state plumbing introduced in US1 and US2
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 Start And Track Bot Processes From One Place**: Can start after Foundational; no dependency on later stories
- **US2 Stop, Restart, And Protect Live Runtime Actions**: Can start after Foundational, but should reuse the runtime/session registration flow introduced in US1
- **US3 Keep Runtime State Explainable In The Monitor**: Can start after Foundational, with best results once runtime lifecycle events from US1 and US2 exist

### Parallel Opportunities

- Setup tasks T002-T003 can run in parallel
- Foundational tasks T006-T010 can run in parallel after the registry model shape is established
- US1 tests T011-T014 can run in parallel
- US2 tests T021-T024 can run in parallel
- US3 tests T031-T033 can run in parallel
- Polish tasks T038-T040 can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Add unit tests for managed runtime creation and running-state registration in tests/unit/test_runtime_manager.py"
Task: "Add unit tests for symbol-scoped log-path derivation and session identity handling in tests/unit/test_runtime_manager.py"
Task: "Add monitor contract tests for required runtime-state fields on instances in tests/contract/test_dashboard_monitor_contract.py"
Task: "Add smoke coverage for starting one managed symbol runtime in tests/smoke/test_runtime_manager_entrypoint.py"
```

## Parallel Example: User Story 2

```text
Task: "Add unit tests for stop-request and graceful stopped-state handling in tests/unit/test_runtime_manager.py"
Task: "Add unit tests for restart session replacement and fresh-session precedence in tests/unit/test_runtime_manager.py"
Task: "Add unit tests for live-safety gating during runtime start and restart in tests/unit/test_runtime_manager.py"
Task: "Add smoke coverage for stop and restart flows in tests/smoke/test_runtime_manager_entrypoint.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Validate that the application can launch and track one or more managed symbol runtimes from its own backend layer.
4. Stop and verify that runtime state appears correctly in the monitor before layering stop/restart controls.

### Incremental Delivery

1. Deliver US1 managed runtime launch and tracking.
2. Add US2 stop/restart and live-safety lifecycle handling.
3. Add US3 runtime-state visibility and operator clarity.
4. Run full validation and update operator documentation.

### Safety Notes

- Keep one managed live process per symbol; do not reintroduce unsupported multi-strategy live execution.
- Reuse current live-trading safeguards instead of inventing a second approval path.
- Preserve symbol-scoped decision, fill, and snapshot evidence so the existing monitor remains trustworthy while runtime state is added.
