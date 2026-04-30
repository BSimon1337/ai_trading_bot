# Tasks: Monitor Runtime Observability

**Input**: Design documents from `/specs/010-monitor-runtime-observability/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include targeted pytest unit, contract, and smoke coverage because this feature changes operator-visible runtime truth, warning visibility, and portfolio-state interpretation for live and paper managed bots.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Align the observability feature artifacts, evidence expectations, and validation path with the current monitor/runtime-manager foundation.

- [x] T001 Review and align observability scope references in `specs/010-monitor-runtime-observability/spec.md`, `specs/010-monitor-runtime-observability/plan.md`, and `README.md`
- [x] T002 [P] Record the normalized observability decisions and card-consistency expectations in `specs/010-monitor-runtime-observability/research.md`
- [x] T003 [P] Confirm runtime event, warning, and portfolio-isolation contract coverage in `specs/010-monitor-runtime-observability/contracts/dashboard-runtime-events-contract.md` and `specs/010-monitor-runtime-observability/contracts/monitor-runtime-observability-contract.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add the shared reconciliation, observability models, and fixture plumbing that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Extend shared monitor observability helpers and constants in `tradingbot/app/monitor.py`
- [x] T005 [P] Add runtime-manager reconciliation support needed by monitor refreshes in `tradingbot/app/runtime_manager.py`
- [x] T006 [P] Add or update monitor configuration defaults for observability limits and event retention in `tradingbot/config/settings.py`
- [x] T007 [P] Expand monitor fixture builders for mixed runtime, warning, and provisional-state scenarios in `tests/fixtures/monitor/build_fixtures.py`
- [x] T008 Add foundational unit coverage for shared observability parsing and reconciliation paths in `tests/unit/test_monitor_data.py` and `tests/unit/test_runtime_manager.py`
- [x] T009 Add foundational contract expectations for the expanded monitor payload in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T010 Add foundational tray-state alignment coverage for reconciled runtime truth in `tests/unit/test_tray_state.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Trust Runtime Truth From The Dashboard (Priority: P1) 🎯 MVP

**Goal**: Make the dashboard runtime state truthful for managed stock and crypto bots, including unexpected exits and stopped-with-history cases.

**Independent Test**: Start, stop, restart, and intentionally interrupt one managed stock bot and one managed crypto bot, then confirm the dashboard matches real runtime truth without using terminal output.

### Tests for User Story 1

- [x] T011 [P] [US1] Add unit coverage for runtime reconciliation and stale-running cleanup in `tests/unit/test_runtime_manager.py`
- [x] T012 [P] [US1] Add monitor data tests for reconciled runtime-state precedence over stale evidence in `tests/unit/test_monitor_data.py`
- [x] T013 [P] [US1] Add contract checks for runtime-state and mode-context payload fields in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T014 [P] [US1] Add smoke coverage for refreshed monitor state after managed runtime transitions in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 1

- [x] T015 [US1] Reconcile managed runtime truth during monitor status assembly in `tradingbot/app/monitor.py`
- [x] T016 [US1] Harden runtime-manager session reconciliation for missing or exited child processes in `tradingbot/app/runtime_manager.py`
- [x] T017 [US1] Standardize badge and mode-context precedence for stock and crypto cards in `tradingbot/app/monitor.py`
- [x] T018 [US1] Render reconciled runtime truth and stopped-vs-historical messaging in `templates/monitor.html`
- [x] T019 [US1] Keep tray runtime summaries aligned with reconciled dashboard truth in `tradingbot/app/tray.py`
- [x] T020 [US1] Preserve correct monitor app refresh behavior for runtime-state changes in `tradingbot/app/monitor_app.py`

**Checkpoint**: User Story 1 should now make the dashboard trustworthy as a source of current runtime truth.

---

## Phase 4: User Story 2 - Understand What The Bot Just Did (Priority: P2)

**Goal**: Surface recent runtime milestones, order lifecycle, and symbol-specific warnings directly in the dashboard.

**Independent Test**: Launch a bot, let it initialize and iterate, trigger or reuse a warning scenario, and confirm the dashboard shows recent runtime events, order progress, and symbol-specific warnings.

### Tests for User Story 2

- [x] T021 [P] [US2] Add unit coverage for runtime event normalization and warning extraction in `tests/unit/test_monitor_data.py`
- [x] T022 [P] [US2] Add unit coverage for runtime-manager lifecycle event shaping in `tests/unit/test_runtime_manager.py`
- [x] T023 [P] [US2] Add contract checks for recent runtime events, warnings, and order lifecycle fields in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T024 [P] [US2] Add tray contract/state coverage for failed and exited runtime outcomes in `tests/contract/test_tray_monitor_contract.py` and `tests/unit/test_tray_state.py`

### Implementation for User Story 2

- [x] T025 [US2] Add normalized recent runtime event and order-lifecycle shaping in `tradingbot/app/monitor.py`
- [x] T026 [US2] Emit or expose monitor-consumable lifecycle and warning evidence through `tradingbot/app/runtime_manager.py`
- [x] T027 [US2] Surface broker, malformed-evidence, and runtime warnings in the dashboard payload in `tradingbot/app/monitor.py`
- [x] T028 [US2] Render recent runtime events, order lifecycle, and warning summaries in `templates/monitor.html`
- [x] T029 [US2] Reflect major failed or exited runtime outcomes in tray summaries in `tradingbot/app/tray.py`

**Checkpoint**: User Story 2 should let the operator explain what a bot just did without opening the terminal.

---

## Phase 5: User Story 3 - See Consistent Portfolio State Across Symbols (Priority: P3)

**Goal**: Keep stock and crypto cards semantically identical and prevent cross-symbol leakage of held quantity, held value, or cash state.

**Independent Test**: Run a mixed stock-and-crypto dashboard, trigger fresh fills before snapshots land, and confirm the cards stay consistent, provisional states are labeled clearly, and no symbol shows another symbol’s portfolio values.

### Tests for User Story 3

- [x] T030 [P] [US3] Add unit coverage for symbol-local effective portfolio-state derivation and leakage prevention in `tests/unit/test_monitor_data.py`
- [x] T031 [P] [US3] Add unit coverage for mixed-symbol runtime and snapshot edge cases in `tests/unit/test_runtime_manager.py`
- [x] T032 [P] [US3] Add contract checks for provisional-state, held-value-source, and freshness fields in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T033 [P] [US3] Add smoke or entrypoint coverage for mixed-symbol refresh consistency in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 3

- [x] T034 [US3] Isolate per-symbol effective portfolio-state derivation in `tradingbot/app/monitor.py`
- [x] T035 [US3] Separate account-overview aggregation from per-symbol held-value calculations in `tradingbot/app/monitor.py`
- [x] T036 [US3] Add explicit provisional-versus-confirmed freshness labeling for symbol cards in `tradingbot/app/monitor.py`
- [x] T037 [US3] Render consistent provisional, unavailable, stale, and historical wording across stock and crypto cards in `templates/monitor.html`
- [x] T038 [US3] Keep tray summary language aligned with the same freshness semantics in `tradingbot/app/tray.py`

**Checkpoint**: All user stories should now be independently functional, and mixed stock/crypto cards should remain consistent after startup and fills.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final documentation, wording cleanup, and full observability validation across all user stories.

- [ ] T039 [P] Update operator documentation for runtime observability behavior in `README.md` and `specs/010-monitor-runtime-observability/quickstart.md`
- [ ] T040 [P] Reconcile dashboard wording and badge/freshness labels across `templates/monitor.html`, `specs/010-monitor-runtime-observability/contracts/`, and `specs/010-monitor-runtime-observability/spec.md`
- [ ] T041 [P] Update launcher or monitor usage notes if needed for mixed-symbol observability validation in `start_monitor.ps1` and `README.md`
- [ ] T042 Run the observability validation bundle from `specs/010-monitor-runtime-observability/quickstart.md` and record outcomes in `specs/010-monitor-runtime-observability/tasks.md`

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
- **User Story 2 (P2)**: Can start after Foundational completion - Builds on the shared observability model but remains independently testable
- **User Story 3 (P3)**: Can start after Foundational completion - Builds on the shared observability model and remains independently testable

### Within Each User Story

- Tests should be written and fail before implementation
- Runtime-manager and monitor payload changes come before template and tray integration
- Event and warning shaping come before UI summaries
- Symbol-local portfolio derivation comes before aggregate account-overview polish
- Story-specific validation should finish before moving to the next priority

### Parallel Opportunities

- `T002` and `T003` can run in parallel during setup
- `T005`, `T006`, and `T007` can run in parallel during the foundational phase
- Within **US1**, `T011` through `T014` can run in parallel, and `T018` plus `T019` can proceed after `T017`
- Within **US2**, `T021` through `T024` can run in parallel, and `T028` can proceed after `T025` through `T027`
- Within **US3**, `T030` through `T033` can run in parallel, and `T037` plus `T038` can proceed after `T034` through `T036`
- `T039`, `T040`, and `T041` can run in parallel during polish

---

## Parallel Example: User Story 2

```bash
# Launch the US2 test work together:
Task: "Add unit coverage for runtime event normalization and warning extraction in tests/unit/test_monitor_data.py"
Task: "Add unit coverage for runtime-manager lifecycle event shaping in tests/unit/test_runtime_manager.py"
Task: "Add contract checks for recent runtime events, warnings, and order lifecycle fields in tests/contract/test_dashboard_monitor_contract.py"
Task: "Add tray contract/state coverage for failed and exited runtime outcomes in tests/contract/test_tray_monitor_contract.py and tests/unit/test_tray_state.py"

# Launch UI/data shaping work after shared event models exist:
Task: "Add normalized recent runtime event and order-lifecycle shaping in tradingbot/app/monitor.py"
Task: "Render recent runtime events, order lifecycle, and warning summaries in templates/monitor.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **Stop and Validate**: Confirm the dashboard matches actual runtime truth for one stock symbol and one crypto symbol through start, stop, and unexpected-exit scenarios
5. Demo the monitor as a trustworthy runtime status surface

### Incremental Delivery

1. Complete Setup + Foundational → observability foundation ready
2. Add User Story 1 → validate runtime truth and badge consistency (MVP)
3. Add User Story 2 → validate event, warning, and order-lifecycle visibility
4. Add User Story 3 → validate symbol-state isolation and provisional portfolio behavior
5. Finish polish and full quickstart validation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 runtime reconciliation and mode/badge consistency
   - Developer B: User Story 2 event feed, warning shaping, and tray alignment
   - Developer C: User Story 3 portfolio-state isolation and provisional-label consistency
3. Merge at story checkpoints and run the quickstart validation bundle

---

## Notes

- [P] tasks = different files, no blocking dependency on unfinished tasks
- [US#] labels map directly to the monitor-runtime-observability spec user stories
- Each user story is designed to be independently demonstrable
- Mixed stock/crypto behavior is a first-class acceptance path, not a cleanup item
- Avoid introducing a new event store or separate frontend when the existing monitor/runtime-manager architecture can express the needed observability
