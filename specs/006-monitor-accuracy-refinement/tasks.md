# Tasks: Monitor Accuracy Refinement

**Input**: Design documents from `/specs/006-monitor-accuracy-refinement/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the plan requires pytest unit, contract, and smoke validation for state aging, held-value fallback, issue-vs-note classification, and retention behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks
- **[Story]**: Maps to user stories from `spec.md`
- Every task includes an exact file path

## Phase 1: Setup

**Purpose**: Prepare the refinement feature scaffolding and document reused monitor patterns.

- [x] T001 Document reused monitor/tray modules, payload contracts, and evidence sources for this refinement in `specs/006-monitor-accuracy-refinement/plan.md`
- [x] T002 [P] Add or refresh monitor refinement fixture notes and sample scenarios in `tests/fixtures/monitor/README.md`
- [x] T003 [P] Review existing monitor contract expectations and capture new payload fields needed by this feature in `specs/006-monitor-accuracy-refinement/contracts/dashboard-monitor-contract.md`

---

## Phase 2: Foundational

**Purpose**: Establish shared monitor evidence rules that all user stories depend on.

**Critical**: No user story work should start until current-versus-historical evidence handling and shared summary helpers are in place.

- [x] T004 Implement shared active-evidence window and historical-evidence filtering helpers in `tradingbot/app/monitor.py`
- [x] T005 Implement shared account-summary source selection and freshness helpers in `tradingbot/app/monitor.py`
- [x] T006 Implement shared value-evidence fallback helpers for per-symbol held-value estimation in `tradingbot/app/monitor.py`
- [x] T007 [P] Add fixture builders or fixture coverage for mixed current/historical, archived, malformed, and no-recent-fill scenarios in `tests/unit/test_monitor_data.py`
- [x] T008 [P] Add foundational unit tests for active-evidence windowing, authoritative summary selection, and held-value fallback helpers in `tests/unit/test_monitor_data.py`

**Checkpoint**: Shared monitor evidence logic is ready for story-specific status, UI, and retention refinements.

---

## Phase 3: User Story 1 - Trust Current Monitor Status (Priority: P1) MVP

**Goal**: Make the dashboard trustworthy as the current source of truth by preferring fresh healthy evidence, showing one authoritative account summary, and displaying reliable held values.

**Independent Test**: Run fixture-driven and contract tests showing a bot restart after older failures, multiple symbol-specific account snapshots, and positions without recent fills, then confirm the dashboard reports current status and trustworthy values.

### Tests for User Story 1

- [x] T009 [P] [US1] Add unit tests for healthy restart precedence over older failed evidence in `tests/unit/test_monitor_data.py`
- [x] T010 [P] [US1] Add unit tests for one authoritative account summary source per refresh in `tests/unit/test_monitor_data.py`
- [x] T011 [P] [US1] Add contract tests for `account_overview`, `held_value`, and `held_value_source` fields in `tests/contract/test_dashboard_monitor_contract.py`

### Implementation for User Story 1

- [x] T012 [US1] Update instance status classification to prefer the latest valid evidence over stale failed history in `tradingbot/app/monitor.py`
- [x] T013 [US1] Refine account overview assembly to use one freshest trusted source in `tradingbot/app/monitor.py`
- [x] T014 [US1] Implement held-value fallback behavior and explicit unavailable-state handling in `tradingbot/app/monitor.py`
- [x] T015 [US1] Update per-instance payload shaping for `held_value`, `held_value_source`, and authoritative account fields in `tradingbot/app/monitor.py`
- [x] T016 [US1] Update dashboard account overview and per-instance cards to reflect the authoritative summary and held-value semantics in `templates/monitor.html`
- [x] T017 [US1] Validate User Story 1 by running `tests/unit/test_monitor_data.py` and `tests/contract/test_dashboard_monitor_contract.py`

**Checkpoint**: The dashboard can be trusted as the current status view for live and paper monitoring.

---

## Phase 4: User Story 2 - Read Problems and Activity Quickly (Priority: P2)

**Goal**: Separate actionable issues from informational notes and expose clearer activity timing and broker rejection context per bot.

**Independent Test**: Run monitor fixtures with warnings, non-critical notes, recent fills, recent decisions, and broker rejections, then confirm the dashboard and tray clearly distinguish notes from issues and expose per-bot activity timing.

### Tests for User Story 2

- [x] T018 [P] [US2] Add unit tests for issue-vs-note classification and broker rejection counting in `tests/unit/test_monitor_data.py`
- [x] T019 [P] [US2] Add contract tests for `notes`, `last_decision_utc`, `last_fill_utc`, and `broker_rejection_count` in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T020 [P] [US2] Add tray unit tests ensuring informational notes do not escalate tray severity in `tests/unit/test_tray_state.py`
- [x] T021 [P] [US2] Add tray contract tests for refined aggregate counts and status summaries in `tests/contract/test_tray_monitor_contract.py`

### Implementation for User Story 2

- [x] T022 [US2] Implement distinct issue and informational note extraction paths in `tradingbot/app/monitor.py`
- [x] T023 [US2] Add last-decision, last-fill, and broker-rejection summary fields to instance aggregation in `tradingbot/app/monitor.py`
- [x] T024 [US2] Update tray state aggregation to use current issue counts while ignoring non-actionable notes in `tradingbot/app/tray.py`
- [x] T025 [US2] Update dashboard sections and per-instance cards to show notes separately from issues and surface activity timestamps/rejection counts in `templates/monitor.html`
- [x] T026 [US2] Validate User Story 2 by running `tests/unit/test_monitor_data.py`, `tests/unit/test_tray_state.py`, `tests/contract/test_dashboard_monitor_contract.py`, and `tests/contract/test_tray_monitor_contract.py`

**Checkpoint**: Operators can distinguish healthy-but-informative context from actual operational problems at a glance.

---

## Phase 5: User Story 3 - Keep Old Evidence from Polluting Current Monitoring (Priority: P3)

**Goal**: Keep active monitoring clean and current while preserving safe access to historical evidence for debugging.

**Independent Test**: Run monitor scenarios with archived, malformed, and older failed evidence alongside current bot activity and confirm active status remains clean while historical problems are bounded and readable.

### Tests for User Story 3

- [x] T027 [P] [US3] Add unit tests for retention-window behavior and bounded historical issue reporting in `tests/unit/test_monitor_data.py`
- [x] T028 [P] [US3] Add contract tests for active-versus-historical status handling in `tests/contract/test_dashboard_monitor_contract.py`
- [x] T029 [P] [US3] Add smoke coverage for monitor startup against mixed current/historical evidence directories in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 3

- [x] T030 [US3] Implement retention-window application and bounded historical-context handling in `tradingbot/app/monitor.py`
- [x] T031 [US3] Add safe log-retention or archival configuration support and default behavior in `tradingbot/app/monitor.py`
- [x] T032 [US3] Surface active-versus-historical evidence context in the dashboard view in `templates/monitor.html`
- [x] T033 [US3] Update tray aggregate-state logic so older failures do not dominate after a healthy restart in `tradingbot/app/tray.py`
- [x] T034 [US3] Document safe retention or archival operating guidance for monitor evidence in `specs/006-monitor-accuracy-refinement/quickstart.md`
- [x] T035 [US3] Validate User Story 3 by running `tests/unit/test_monitor_data.py`, `tests/contract/test_dashboard_monitor_contract.py`, `tests/unit/test_tray_state.py`, and `tests/smoke/test_monitor_entrypoint.py`

**Checkpoint**: Historical evidence remains useful for debugging without contaminating the current monitor view.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, documentation, and validation across all monitor-refinement stories.

- [x] T036 [P] Review monitor payload and UI naming for consistency with the refined contracts in `tradingbot/app/monitor.py` and `templates/monitor.html`
- [x] T037 [P] Update operator-facing monitor usage notes and troubleshooting in `README.md`
- [x] T038 [P] Confirm no new dependency or live-control behavior was introduced in `specs/006-monitor-accuracy-refinement/research.md` and `tradingbot/app/tray.py`
- [x] T039 Run full monitor-related validation from `specs/006-monitor-accuracy-refinement/quickstart.md`
- [x] T040 Record manual validation notes for mixed-evidence monitoring scenarios in `specs/006-monitor-accuracy-refinement/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational and builds on the refined instance payload from US1
- **User Story 3 (Phase 5)**: Depends on Foundational and benefits from US1 status precedence plus US2 issue/note separation
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 Trust Current Monitor Status**: Can start after Foundational; no dependency on later stories
- **US2 Read Problems and Activity Quickly**: Can start after Foundational, but should use the refined payload semantics from US1
- **US3 Keep Old Evidence from Polluting Current Monitoring**: Can start after Foundational, with best results once US1 precedence rules are in place

### Parallel Opportunities

- Setup tasks T002-T003 can run in parallel
- Foundational tests T007-T008 can run in parallel after helper design begins
- US1 tests T009-T011 can run in parallel
- US2 tests T018-T021 can run in parallel
- US3 tests T027-T029 can run in parallel
- Polish docs and consistency tasks T036-T038 can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Add unit tests for healthy restart precedence over older failed evidence in tests/unit/test_monitor_data.py"
Task: "Add unit tests for one authoritative account summary source per refresh in tests/unit/test_monitor_data.py"
Task: "Add contract tests for account_overview, held_value, and held_value_source fields in tests/contract/test_dashboard_monitor_contract.py"
```

## Parallel Example: User Story 2

```text
Task: "Add unit tests for issue-vs-note classification and broker rejection counting in tests/unit/test_monitor_data.py"
Task: "Add tray unit tests ensuring informational notes do not escalate tray severity in tests/unit/test_tray_state.py"
Task: "Add tray contract tests for refined aggregate counts and status summaries in tests/contract/test_tray_monitor_contract.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Validate that current-state trust, held-value fallback, and authoritative account overview behave correctly.
4. Stop and verify the dashboard is trustworthy before layering operator-clarity and retention refinements.

### Incremental Delivery

1. Deliver US1 current-state trust and authoritative account metrics.
2. Add US2 operator-clarity improvements for notes, timestamps, and rejection counts.
3. Add US3 historical-evidence hygiene and retention handling.
4. Run full validation and update operator documentation.

### Safety Notes

- Keep the monitor and tray strictly read-only.
- Do not introduce broker polling, order placement, or live-approval behavior in this feature.
- Preserve historical evidence for debugging even when active monitoring ignores it for current-state classification.
