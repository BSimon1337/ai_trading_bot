# Tasks: Dashboard and Tray App

**Input**: Design documents from `/specs/004-dashboard-tray-app/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the plan requires pytest unit, smoke, and contract-style validation for monitor data shaping, dashboard routes, tray state/menu behavior, malformed logs, and read-only safety.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks
- **[Story]**: Maps to user stories from `spec.md`
- Every task includes an exact file path

## Phase 1: Setup

**Purpose**: Add pinned tray dependencies and establish monitor module/test locations.

- [x] T001 Add pinned `pystray==0.19.5` and `Pillow==11.3.0` dependencies to `requirements.txt`
- [x] T002 Add pinned `pystray==0.19.5` and `Pillow==11.3.0` dependencies to `pyproject.toml`
- [x] T003 [P] Create monitor package module placeholder in `tradingbot/app/monitor.py`
- [x] T004 [P] Create tray package module placeholder in `tradingbot/app/tray.py`
- [x] T005 [P] Create contract test directory placeholder in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T006 [P] Create tray contract test directory placeholder in `tests/contract/test_tray_monitor_contract.py`
- [x] T007 [P] Create fixture directory documentation in `tests/fixtures/monitor/README.md`

---

## Phase 2: Foundational

**Purpose**: Core monitor data parsing and configuration shared by all user stories.

**Critical**: No user story implementation should start until the monitor data model and fixture helpers are ready.

- [x] T008 Define monitor dataclasses for MonitorConfiguration, DashboardInstance, RuntimeStatus, DecisionSummary, FillSummary, SnapshotSummary, IssueSummary, and TrayState in `tradingbot/app/monitor.py`
- [x] T009 Implement safe CSV reader and timestamp/numeric normalization helpers in `tradingbot/app/monitor.py`
- [x] T010 Implement configured monitor instance discovery from existing log paths and symbols in `tradingbot/app/monitor.py`
- [x] T011 Implement secret-redaction helper for dashboard/tray payloads in `tradingbot/app/monitor.py`
- [x] T012 [P] Add monitor fixture builders for healthy, no-data, malformed, stale, blocked-live, failed, and broker-rejection CSV evidence in `tests/fixtures/monitor/build_fixtures.py`
- [x] T013 [P] Add unit tests for safe CSV parsing and malformed evidence handling in `tests/unit/test_monitor_data.py`
- [x] T014 [P] Add unit tests for secret redaction and slash-form crypto symbol handling in `tests/unit/test_monitor_data.py`

**Checkpoint**: Monitor foundation can parse fixture evidence without network access or trading side effects.

---

## Phase 3: User Story 1 - View Trading Bot Status (Priority: P1) MVP

**Goal**: Provide a browser dashboard that shows bot status, symbols, modes, latest decisions, latest fills, and no-data states from existing runtime evidence.

**Independent Test**: Run dashboard contract and route tests against fixture logs and confirm `/`, `/health`, and `/api/status` expose readable status without credentials or crashes.

### Tests for User Story 1

- [x] T015 [P] [US1] Add contract tests for `GET /`, `GET /health`, and `GET /api/status` in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T016 [P] [US1] Add route smoke tests for dashboard startup and no-data rendering in `tests/smoke/test_monitor_entrypoint.py`
- [x] T017 [P] [US1] Add unit tests for dashboard status aggregation across at least 10 fixture instances in `tests/unit/test_monitor_data.py`

### Implementation for User Story 1

- [x] T018 [US1] Implement dashboard status aggregation and instance summaries in `tradingbot/app/monitor.py`
- [x] T019 [US1] Implement Flask app factory, `/`, `/health`, and `/api/status` routes in `tradingbot/app/monitor.py`
- [x] T020 [US1] Refactor root compatibility entrypoint to use the monitor app factory in `monitor_app.py`
- [x] T021 [US1] Update dashboard cards, recent decisions, recent fills, no-data states, and auto-refresh behavior in `templates/monitor.html`
- [x] T022 [US1] Ensure dashboard output excludes credentials and sensitive environment values in `tradingbot/app/monitor.py`
- [x] T023 [US1] Validate User Story 1 by running dashboard contract, unit, and smoke tests in `tests/contract/test_dashboard_monitor_contract.py`, `tests/unit/test_monitor_data.py`, and `tests/smoke/test_monitor_entrypoint.py`

**Checkpoint**: Browser dashboard MVP is independently usable and read-only.

---

## Phase 4: User Story 2 - See Tray Presence While Running (Priority: P2)

**Goal**: Provide a system tray presence with status summary, Open Dashboard, Refresh Status, and Exit Monitor actions.

**Independent Test**: Run tray contract/unit tests with mocked tray dependencies and verify menu actions do not touch trading APIs or kill bot processes.

### Tests for User Story 2

- [x] T024 [P] [US2] Add tray contract tests for startup, state values, menu labels, and degraded mode in `tests/contract/test_tray_monitor_contract.py`
- [x] T025 [P] [US2] Add unit tests for tray state mapping from dashboard aggregate status in `tests/unit/test_tray_state.py`
- [x] T026 [P] [US2] Add unit tests proving tray actions do not call trading order APIs in `tests/unit/test_tray_state.py`

### Implementation for User Story 2

- [x] T027 [US2] Implement tray state mapping and tooltip/menu model in `tradingbot/app/tray.py`
- [x] T028 [US2] Implement pystray icon creation, Open Dashboard, Refresh Status, and Exit Monitor actions in `tradingbot/app/tray.py`
- [x] T029 [US2] Implement graceful tray-unavailable fallback that keeps the browser dashboard usable in `tradingbot/app/tray.py`
- [x] T030 [US2] Add monitor/tray command handling and safe defaults in `tradingbot/app/tray.py`
- [x] T031 [US2] Validate User Story 2 by running tray contract and unit tests in `tests/contract/test_tray_monitor_contract.py` and `tests/unit/test_tray_state.py`

**Checkpoint**: Tray presence works through mocked tests and degrades safely.

---

## Phase 5: User Story 3 - Identify Problems Quickly (Priority: P3)

**Goal**: Highlight blocked live runs, stale market data, dependency warnings, disconnected processes, broker/order errors, malformed logs, and no-data states.

**Independent Test**: Run fixture-state tests and confirm every configured state maps to a distinct dashboard/tray status and recent issue summary.

### Tests for User Story 3

- [ ] T032 [P] [US3] Add fixture-state unit tests for blocked-live, stale, failed, malformed, broker-rejection, and no-data states in `tests/unit/test_monitor_data.py`
- [ ] T033 [P] [US3] Add dashboard contract tests for recent issues and critical status rendering in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T034 [P] [US3] Add tray status tests for warning and critical issue aggregation in `tests/unit/test_tray_state.py`

### Implementation for User Story 3

- [ ] T035 [US3] Implement issue extraction from decision, fill, snapshot, and run-event evidence in `tradingbot/app/monitor.py`
- [ ] T036 [US3] Implement stale/blocked/failed/no-data status classification rules in `tradingbot/app/monitor.py`
- [ ] T037 [US3] Add recent issues panel and distinct status styling in `templates/monitor.html`
- [ ] T038 [US3] Integrate issue severity with tray state and tooltip text in `tradingbot/app/tray.py`
- [ ] T039 [US3] Validate User Story 3 by running monitor data, dashboard contract, and tray state tests in `tests/unit/test_monitor_data.py`, `tests/contract/test_dashboard_monitor_contract.py`, and `tests/unit/test_tray_state.py`

**Checkpoint**: Problem states are visible without reading raw logs.

---

## Phase 6: User Story 4 - Run as a Local App Experience (Priority: P4)

**Goal**: Let the operator start the monitor from a single documented command and understand how to open, watch, and stop it.

**Independent Test**: Run the monitor command smoke test and follow quickstart steps to confirm the dashboard/tray monitor starts cleanly and exits without stopping trading bot processes.

### Tests for User Story 4

- [ ] T040 [P] [US4] Add smoke tests for `python -m tradingbot.app.tray --no-tray` and monitor startup behavior in `tests/smoke/test_monitor_entrypoint.py`
- [ ] T041 [P] [US4] Add smoke tests for root `monitor_app.py` compatibility in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 4

- [ ] T042 [US4] Add CLI options for dashboard host, dashboard port, refresh seconds, `--no-tray`, and read-only mode in `tradingbot/app/tray.py`
- [ ] T043 [US4] Add package script entry for the monitor command in `pyproject.toml`
- [ ] T044 [US4] Update dashboard/tray launch instructions, stop instructions, and troubleshooting notes in `README.md`
- [ ] T045 [US4] Update feature quickstart with final commands and validation results in `specs/004-dashboard-tray-app/quickstart.md`
- [ ] T046 [US4] Validate User Story 4 by running smoke tests in `tests/smoke/test_monitor_entrypoint.py`

**Checkpoint**: Monitor can be launched and explained like a local application.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, dependency discipline, documentation consistency, and operator evidence.

- [ ] T047 [P] Re-verify dependency pinning and age notes for `pystray==0.19.5` and `Pillow==11.3.0` in `specs/004-dashboard-tray-app/research.md`
- [ ] T048 [P] Add dashboard/tray troubleshooting entries for blank windows, wrong working directory, missing logs, and tray unavailable state in `README.md`
- [ ] T049 [P] Ensure monitor-specific generated files and runtime artifacts are ignored or documented in `.gitignore`
- [ ] T050 Run full test suite with `.\.venv\Scripts\python.exe -m pytest`
- [ ] T051 Manually validate quickstart launch flow and record observed dashboard/tray evidence in `specs/004-dashboard-tray-app/quickstart.md`
- [ ] T052 Review dashboard/tray code for read-only safety and confirm no trading order APIs are called from `tradingbot/app/monitor.py` or `tradingbot/app/tray.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational and can proceed after US1 contracts establish status payloads
- **User Story 3 (Phase 5)**: Depends on US1 status aggregation and benefits from US2 tray state mapping
- **User Story 4 (Phase 6)**: Depends on US1 and US2 for launchable monitor behavior
- **Polish (Phase 7)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 View Trading Bot Status**: Start after Foundational; no dependency on tray
- **US2 See Tray Presence While Running**: Start after Foundational; uses US1 status model when available
- **US3 Identify Problems Quickly**: Start after US1 status model; integrates with tray state from US2
- **US4 Run as a Local App Experience**: Start after US1 and US2 provide dashboard/tray launch targets

### Parallel Opportunities

- Setup placeholders T003-T007 can run in parallel
- Foundational fixture and parsing tests T012-T014 can run in parallel after T008-T011 are outlined
- US1 tests T015-T017 can run in parallel
- US2 tests T024-T026 can run in parallel
- US3 tests T032-T034 can run in parallel
- US4 tests T040-T041 can run in parallel
- Polish documentation checks T047-T049 can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Add contract tests for GET /, GET /health, and GET /api/status in tests/contract/test_dashboard_monitor_contract.py"
Task: "Add route smoke tests for dashboard startup and no-data rendering in tests/smoke/test_monitor_entrypoint.py"
Task: "Add unit tests for dashboard status aggregation across at least 10 fixture instances in tests/unit/test_monitor_data.py"
```

## Parallel Example: User Story 2

```text
Task: "Add tray contract tests for startup, state values, menu labels, and degraded mode in tests/contract/test_tray_monitor_contract.py"
Task: "Add unit tests for tray state mapping from dashboard aggregate status in tests/unit/test_tray_state.py"
Task: "Add unit tests proving tray actions do not call trading order APIs in tests/unit/test_tray_state.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Validate that the browser dashboard works independently with fixture logs and existing runtime evidence.
4. Stop and demo before adding tray behavior.

### Incremental Delivery

1. Deliver US1 browser dashboard MVP.
2. Add US2 tray presence.
3. Add US3 richer issue/status visibility.
4. Add US4 local-app launch polish.
5. Run full validation and quickstart checks.

### Safety Notes

- Keep dashboard/tray behavior read-only unless a future spec explicitly designs process controls.
- Do not add trade approval, order placement, cancellation, or live-safeguard changes in this feature.
- Avoid committing generated runtime logs unless intentionally preserving manual validation evidence.
