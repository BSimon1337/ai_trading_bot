# Tasks: Preflight Validation and Offline News Mode

**Input**: Design documents from `/specs/003-preflight-offline-mode/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/preflight-cli-contract.md`, `quickstart.md`

**Tests**: Required by the feature plan for readiness reporting, Alpaca News failure handling, fixture loading, log-path checks, model-load diagnostics, and live safeguard blocking.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches independent files or has no dependency on sibling task output
- **[Story]**: User story label, such as `[US1]`, `[US2]`, or `[US3]`
- Include exact file paths in task descriptions

## Phase 1: Setup

**Purpose**: Confirm the feature workspace and document the conventions before implementation begins.

- [x] T001 Verify the active feature pointer and plan artifacts are aligned in `.specify/feature.json` and `specs/003-preflight-offline-mode/plan.md`
- [x] T002 [P] Add the offline fixture directory convention to `data/offline_news/README.md`
- [x] T003 [P] Document preflight and offline-mode environment switches in `specs/003-preflight-offline-mode/quickstart.md`
- [x] T004 [P] Confirm no new dependency additions are required beyond pinned `requirements.txt` and `pyproject.toml`

---

## Phase 2: Foundational

**Purpose**: Add shared structures and integration points that all stories depend on.

**Critical**: Complete this phase before starting any user story implementation.

- [ ] T005 Create `ReadinessStatus`, `ReadinessCheckResult`, and `ReadinessReport` helpers in `tradingbot/app/preflight.py`
- [ ] T006 [P] Add offline news fixture dataclasses and parsing helpers in `tradingbot/data/offline_news.py`
- [ ] T007 [P] Add sentiment data-source fields to decision logging helpers in `tradingbot/execution/logging.py`
- [ ] T008 Add preflight mode and CLI flag contract wiring in `tradingbot/app/main.py`
- [ ] T009 [P] Add shared test fixtures or builders in `tests/conftest.py` if duplicated setup appears during tests

---

## Phase 3: User Story 1 - Validate Readiness Before Running (Priority: P1)

**Goal**: A user can run one command to learn whether the bot is safe and ready to run in paper/backtest/live mode.

**Independent Test**: Run the preflight CLI with mocked pass, warning, and failure scenarios; verify operator-readable output and fail-closed exit codes without placing trades.

### Tests for User Story 1

- [ ] T010 [P] [US1] Add readiness pass, warning, and fail unit tests in `tests/unit/test_preflight_readiness.py`
- [ ] T011 [P] [US1] Add log-path readiness tests in `tests/unit/test_log_path_readiness.py`
- [ ] T012 [P] [US1] Add preflight CLI smoke tests in `tests/smoke/test_preflight_entrypoint.py`

### Implementation for User Story 1

- [ ] T013 [US1] Implement credential presence and symbol classification checks in `tradingbot/app/preflight.py`
- [ ] T014 [US1] Implement log path writability and creatability checks in `tradingbot/app/preflight.py`
- [ ] T015 [US1] Implement Alpaca trading, market data, and news probe checks with safe exception handling in `tradingbot/app/preflight.py`
- [ ] T016 [US1] Implement live safeguard readiness checks using `tradingbot/execution/safeguards.py`
- [ ] T017 [US1] Wire preflight mode output and exit codes into `tradingbot/app/main.py`
- [ ] T018 [US1] Add preflight run event logging through `tradingbot/execution/logging.py`
- [ ] T019 [US1] Update preflight pass, warning, and fail examples in `specs/003-preflight-offline-mode/quickstart.md`

---

## Phase 4: User Story 2 - Backtest With Offline News (Priority: P2)

**Goal**: A user can run backtests when Alpaca News or network access is unavailable by using local or cached news fixtures.

**Independent Test**: Run a backtest path with external news disabled and a local fixture present; verify fixture headlines are used and decision logs record the source.

### Tests for User Story 2

- [ ] T020 [P] [US2] Add fixture parser and validation tests in `tests/unit/test_offline_news_fixtures.py`
- [ ] T021 [P] [US2] Add offline-news backtest routing smoke coverage in `tests/smoke/test_backtest_entrypoint.py`

### Implementation for User Story 2

- [ ] T022 [US2] Implement local and cached news fixture loading in `tradingbot/data/offline_news.py`
- [ ] T023 [US2] Add config and environment support for offline mode and fixture directory in `tradingbot/config/settings.py`
- [ ] T024 [US2] Integrate offline fixture fallback into headline retrieval in `tradingbot/data/news.py`
- [ ] T025 [US2] Record sentiment source values such as `external`, `local_fixture`, and `neutral_fallback` in `tradingbot/strategy/lumibot_strategy.py`
- [ ] T026 [US2] Extend decision logging headers and append logic for sentiment source in `tradingbot/execution/logging.py`
- [ ] T027 [US2] Add sanitized sample fixture documentation under `data/offline_news/`
- [ ] T028 [US2] Update the offline backtest flow in `specs/003-preflight-offline-mode/quickstart.md`

---

## Phase 5: User Story 3 - Diagnose Optional Model and Dependency Gaps (Priority: P3)

**Goal**: A user can distinguish hard blockers from optional model or dependency warnings before running the bot.

**Independent Test**: Run preflight with missing optional model files or optional sentiment dependencies; verify warnings are reported without crashing, while required dependency failures block execution.

### Tests for User Story 3

- [ ] T029 [P] [US3] Add dependency diagnostic tests in `tests/unit/test_preflight_readiness.py`
- [ ] T030 [P] [US3] Extend model fallback coverage for preflight model-load warnings in `tests/unit/test_model_fallback.py`

### Implementation for User Story 3

- [ ] T031 [US3] Implement required and optional dependency diagnostics in `tradingbot/app/preflight.py`
- [ ] T032 [US3] Implement saved-model loadability diagnostics without crashing in `tradingbot/app/preflight.py`
- [ ] T033 [US3] Add optional sentiment and FinBERT availability diagnostics in `tradingbot/app/preflight.py`
- [ ] T034 [US3] Ensure CLI diagnostics distinguish required failures from optional warnings in `tradingbot/app/preflight.py`
- [ ] T035 [US3] Document optional dependency behavior in `specs/003-preflight-offline-mode/quickstart.md`

---

## Phase 6: Polish and Cross-Cutting Verification

**Purpose**: Validate the full feature, preserve safety guarantees, and avoid committing generated runtime artifacts.

- [ ] T036 Run the targeted test suite covering `tests/unit/test_preflight_readiness.py`, `tests/unit/test_offline_news_fixtures.py`, `tests/unit/test_log_path_readiness.py`, `tests/unit/test_model_fallback.py`, `tests/smoke/test_preflight_entrypoint.py`, and `tests/smoke/test_paper_mode_guardrails.py`
- [ ] T037 Run the quick preflight command manually and record expected results in `specs/003-preflight-offline-mode/quickstart.md`
- [ ] T038 Verify no new dependencies or npm packages were introduced in `requirements.txt` and `pyproject.toml`
- [ ] T039 Verify live mode remains fail-closed through `tests/smoke/test_paper_mode_guardrails.py`
- [ ] T040 Review operator-visible log and CSV evidence for sentiment source and readiness events without committing runtime files under `logs/`
- [ ] T041 Update `specs/003-preflight-offline-mode/tasks.md` task checkboxes as implementation progresses

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup completion
- **US1 (Phase 3)**: Depends on Foundational; highest priority MVP
- **US2 (Phase 4)**: Depends on Foundational; can proceed after US1 is stable or in parallel with US1 after shared interfaces are agreed
- **US3 (Phase 5)**: Depends on Foundational; can proceed after US1 preflight reporting structure exists
- **Polish (Phase 6)**: Depends on all selected stories being complete

### Story Dependencies

- **US1**: No story dependency after Foundational; establishes preflight report and exit-code behavior
- **US2**: Depends on offline fixture helpers from Foundational; uses existing news and strategy flow
- **US3**: Depends on the preflight reporting structure from US1 to present warnings vs failures consistently

### Within Each User Story

- Write and confirm failing tests first
- Implement the smallest code path needed to satisfy tests
- Wire CLI or strategy integration after core helpers exist
- Update quickstart documentation after behavior is stable

### Parallel Opportunities

- T002, T003, and T004 can run in parallel during Setup
- T006, T007, and T009 can run in parallel during Foundational
- T010, T011, and T012 can run in parallel for US1 tests
- T020 and T021 can run in parallel for US2 tests
- T029 and T030 can run in parallel for US3 tests
- US2 fixture work can proceed in parallel with US1 once `ReadinessReport` structure is in place

---

## Implementation Strategy

### MVP First: User Story 1

1. Complete Phase 1 and Phase 2.
2. Complete US1 tests T010-T012.
3. Complete US1 implementation T013-T019.
4. Verify preflight returns safe exit codes and never places trades.

### Incremental Delivery

1. Deliver US1 for readiness and live-safety visibility.
2. Add US2 to unblock backtests when Alpaca News is unavailable.
3. Add US3 to improve dependency and model diagnostics.
4. Run Phase 6 checks before merge or release.
