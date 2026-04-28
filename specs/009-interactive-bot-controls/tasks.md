# Tasks: Interactive Bot Controls

**Input**: Design documents from `/specs/009-interactive-bot-controls/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include targeted pytest unit, contract, and smoke coverage because this feature changes live operator control behavior and must preserve runtime safety.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the interactive-control feature scaffolding and align docs/contracts with the current runtime-manager foundation.

- [x] T001 Review and align interactive-control scope references in `specs/009-interactive-bot-controls/plan.md`, `specs/009-interactive-bot-controls/quickstart.md`, and `README.md`
- [x] T002 [P] Record runtime-manager reuse points and interactive-control touchpoints in `specs/009-interactive-bot-controls/research.md`
- [x] T003 [P] Confirm stock-plus-crypto coverage expectations and operator-safe wording in `specs/009-interactive-bot-controls/contracts/dashboard-control-contract.md` and `specs/009-interactive-bot-controls/contracts/monitor-control-contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the shared control data structures and monitor/runtime plumbing that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Extend runtime-registry data structures for recent control actions in `tradingbot/app/runtime_manager.py`
- [x] T005 [P] Add configuration defaults and limits for control-activity retention in `tradingbot/config/settings.py`
- [x] T006 [P] Add monitor-side parsing helpers for control availability and recent control history in `tradingbot/app/monitor.py`
- [x] T007 [P] Add shared runtime-manager unit fixtures for stock and crypto managed symbols in `tests/unit/test_runtime_manager.py`
- [x] T008 Add foundational monitor/runtime tests for control-state parsing and registry persistence in `tests/unit/test_monitor_data.py` and `tests/unit/test_runtime_manager.py`
- [x] T009 Update monitor fixture builders for mixed stock/crypto managed-control scenarios in `tests/fixtures/monitor/build_fixtures.py`
- [x] T010 Verify foundational dashboard payload compatibility in `tests/contract/test_dashboard_monitor_contract.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Control One Managed Bot From The Dashboard (Priority: P1) 🎯 MVP

**Goal**: Let the operator start, stop, and restart one managed symbol directly from the dashboard for both a stock symbol and a crypto symbol.

**Independent Test**: Open the dashboard, issue start/stop/restart for one stock symbol and one crypto symbol, and confirm runtime state changes without CLI commands.

### Tests for User Story 1

- [x] T011 [P] [US1] Add contract coverage for dashboard control action results in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T012 [P] [US1] Add runtime-manager lifecycle tests for dashboard-issued start/stop/restart flows in `tests/unit/test_runtime_manager.py`
- [x] T013 [P] [US1] Add monitor payload tests for per-symbol control availability in `tests/unit/test_monitor_data.py`
- [x] T014 [P] [US1] Add smoke coverage for dashboard control routes in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 1

- [x] T015 [US1] Add dashboard control request handlers for start/stop/restart in `tradingbot/app/monitor.py`
- [x] T016 [US1] Add runtime-manager action entrypoints used by the monitor in `tradingbot/app/runtime_manager.py`
- [x] T017 [US1] Add per-symbol control availability fields to monitor status shaping in `tradingbot/app/monitor.py`
- [x] T018 [US1] Render start/stop/restart controls and runtime action feedback in `templates/monitor.html`
- [x] T019 [US1] Keep tray/runtime summaries aligned with dashboard-issued action outcomes in `tradingbot/app/tray.py`
- [x] T020 [US1] Verify control affordances remain visible for both stock and crypto managed symbols in `tradingbot/app/monitor.py` and `templates/monitor.html`

**Checkpoint**: User Story 1 should now allow basic dashboard lifecycle control for one managed symbol of either asset type.

---

## Phase 4: User Story 2 - Safely Confirm Live Control Actions (Priority: P2)

**Goal**: Require clear live confirmation and preserve current safeguards for dashboard-issued live control actions.

**Independent Test**: Attempt live and paper dashboard actions and confirm live control requires explicit confirmation while blocked actions surface clear reasons.

### Tests for User Story 2

- [ ] T021 [P] [US2] Add unit coverage for live-confirmation and blocked-action logic in `tests/unit/test_runtime_manager.py`
- [ ] T022 [P] [US2] Add monitor data tests for live-vs-paper control messaging in `tests/unit/test_monitor_data.py`
- [ ] T023 [P] [US2] Add contract checks for live confirmation requirements in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T024 [P] [US2] Add smoke tests for live control confirmation flow in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 2

- [ ] T025 [US2] Add monitor-side live confirmation state and validation flow in `tradingbot/app/monitor.py`
- [ ] T026 [US2] Enforce dashboard-issued live safeguard checks through runtime-manager control calls in `tradingbot/app/runtime_manager.py`
- [ ] T027 [US2] Render explicit live confirmation and blocked-action messaging in `templates/monitor.html`
- [ ] T028 [US2] Surface live-vs-paper context consistently in tray and status summaries in `tradingbot/app/tray.py` and `tradingbot/app/monitor.py`
- [ ] T029 [US2] Ensure blocked actions produce readable operator-visible outcomes in `tradingbot/app/monitor.py`

**Checkpoint**: User Story 2 should preserve the live-trading safety posture while making control decisions understandable in the UI.

---

## Phase 5: User Story 3 - See Recent Control Activity And Coverage Across Asset Types (Priority: P3)

**Goal**: Show recent control history and keep mixed stock/crypto control behavior understandable and auditable.

**Independent Test**: Manage one stock symbol and one crypto symbol from the dashboard, refresh the page, and confirm recent activity and coverage remain visible without terminal inspection.

### Tests for User Story 3

- [ ] T030 [P] [US3] Add unit tests for recent control activity retention and ordering in `tests/unit/test_runtime_manager.py`
- [ ] T031 [P] [US3] Add monitor data tests for mixed stock/crypto recent control history in `tests/unit/test_monitor_data.py`
- [ ] T032 [P] [US3] Add contract checks for recent control activity payload fields in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T033 [P] [US3] Add tray contract/state coverage for reflected control outcomes in `tests/contract/test_tray_monitor_contract.py` and `tests/unit/test_tray_state.py`

### Implementation for User Story 3

- [ ] T034 [US3] Persist bounded recent control activity in the runtime registry in `tradingbot/app/runtime_manager.py`
- [ ] T035 [US3] Add recent control activity and control refresh fields to monitor payload shaping in `tradingbot/app/monitor.py`
- [ ] T036 [US3] Render recent control activity and mixed asset context in `templates/monitor.html`
- [ ] T037 [US3] Reflect latest control-related runtime outcomes in tray summaries in `tradingbot/app/tray.py`
- [ ] T038 [US3] Keep stock and crypto control history readable under quiet-trading conditions in `tradingbot/app/monitor.py`

**Checkpoint**: All user stories should now be independently functional, and the dashboard should feel like a coherent operator console.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, docs, safety review, and full-feature validation across all user stories.

- [ ] T039 [P] Update operator documentation for dashboard controls in `README.md` and `specs/009-interactive-bot-controls/quickstart.md`
- [ ] T040 [P] Reconcile wording and labels across monitor UI, contracts, and spec docs in `templates/monitor.html`, `specs/009-interactive-bot-controls/contracts/`, and `specs/009-interactive-bot-controls/spec.md`
- [ ] T041 Run the interactive-control validation bundle from `specs/009-interactive-bot-controls/quickstart.md` and record outcomes in `specs/009-interactive-bot-controls/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel if desired
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational completion - No dependency on other stories
- **User Story 2 (P2)**: Can start after Foundational completion - Builds safely on the action path from US1 but remains independently testable
- **User Story 3 (P3)**: Can start after Foundational completion - Builds on the control evidence path and remains independently testable

### Within Each User Story

- Tests should be written and fail before implementation
- Runtime-manager and monitor payload changes come before template/tray integration
- Control state and outcome shaping come before recent-history polish
- Story-specific validation should finish before moving to the next priority

### Parallel Opportunities

- `T002` and `T003` can run in parallel during setup
- `T005`, `T006`, `T007`, and `T009` can run in parallel during the foundational phase
- Within **US1**, `T011` through `T014` can run in parallel, and `T018` can proceed after `T017`
- Within **US2**, `T021` through `T024` can run in parallel, and `T027` can proceed after `T025`
- Within **US3**, `T030` through `T033` can run in parallel, and `T036` can proceed after `T035`
- `T039` and `T040` can run in parallel during polish

---

## Parallel Example: User Story 1

```bash
# Launch the US1 test work together:
Task: "Add contract coverage for dashboard control action results in tests/contract/test_dashboard_monitor_contract.py"
Task: "Add runtime-manager lifecycle tests for dashboard-issued start/stop/restart flows in tests/unit/test_runtime_manager.py"
Task: "Add monitor payload tests for per-symbol control availability in tests/unit/test_monitor_data.py"
Task: "Add smoke coverage for dashboard control routes in tests/smoke/test_monitor_entrypoint.py"

# Launch UI/data shaping work after shared handlers exist:
Task: "Add per-symbol control availability fields to monitor status shaping in tradingbot/app/monitor.py"
Task: "Render start/stop/restart controls and runtime action feedback in templates/monitor.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **Stop and Validate**: Confirm dashboard control works for one stock symbol and one crypto symbol without CLI commands
5. Demo the monitor as a true operator control surface

### Incremental Delivery

1. Complete Setup + Foundational → control foundation ready
2. Add User Story 1 → validate basic dashboard lifecycle control (MVP)
3. Add User Story 2 → validate live-safe confirmation behavior
4. Add User Story 3 → validate recent control history and mixed asset clarity
5. Finish polish and full quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 control routes and runtime integration
   - Developer B: User Story 2 live confirmation and safeguard messaging
   - Developer C: User Story 3 recent control history and tray alignment
3. Merge at story checkpoints and run the quickstart validation bundle

---

## Notes

- [P] tasks = different files, no blocking dependency on unfinished tasks
- [US#] labels map directly to the interactive-controls spec user stories
- Each user story is designed to be independently demonstrable
- Stock support is intentionally part of the acceptance path, not a future retrofit
- Avoid turning the tray into the main control surface in this feature
