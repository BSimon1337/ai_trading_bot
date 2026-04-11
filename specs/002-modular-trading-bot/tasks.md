---

description: "Task list for Modular Multi-Asset Trading Bot implementation"
---

# Tasks: Modular Multi-Asset Trading Bot

**Input**: Design documents from `/specs/002-modular-trading-bot/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include `pytest` unit tests for signal logic and sizing plus smoke validation for backtest and paper-mode guardrails.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Application package: `tradingbot/`
- Tests: `tests/unit/`, `tests/smoke/`
- Existing operator dashboard remains at repository root in `monitor_app.py`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish package layout, tool configuration, and documentation anchors for the refactor

- [x] T001 Create package directories and `__init__.py` files for `tradingbot/config`, `tradingbot/data`, `tradingbot/sentiment`, `tradingbot/strategy`, `tradingbot/risk`, `tradingbot/execution`, and `tradingbot/app`
- [x] T002 [P] Create test directories and package markers in `tests/unit`, `tests/smoke`, and `tests/__init__.py`
- [x] T003 [P] Document the retained repo patterns and migration targets in `specs/002-modular-trading-bot/plan.md`
- [x] T004 [P] Record Python 3.10 and `pytest` runtime expectations in `specs/002-modular-trading-bot/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the shared runtime primitives that every user story depends on

**Critical**: No user story work should begin until this phase is complete

- [x] T005 Implement centralized environment-backed settings loading in `tradingbot/config/settings.py`
- [x] T006 [P] Implement execution mode and two-step live safeguard validation in `tradingbot/execution/safeguards.py`
- [x] T007 [P] Implement shared execution logging helpers for decisions, fills, and run-mode events in `tradingbot/execution/logging.py`
- [x] T008 [P] Implement risk sizing and guardrail primitives in `tradingbot/risk/sizing.py`
- [x] T009 Implement broker/runtime wiring for Lumibot and Alpaca access in `tradingbot/execution/broker.py`
- [x] T010 Implement main app routing entrypoint for `backtest`, `paper`, and `live` modes in `tradingbot/app/main.py`
- [x] T011 Update legacy imports in `tradingbot.py` to delegate to `tradingbot/app/main.py`
- [x] T012 Add smoke coverage for backtest entrypoint routing in `tests/smoke/test_backtest_entrypoint.py`
- [x] T013 Add smoke coverage for paper/live guardrail enforcement in `tests/smoke/test_paper_mode_guardrails.py`

**Checkpoint**: Shared runtime, safeguards, and logging are ready for story implementation

---

## Phase 3: User Story 1 - Run the Bot Through Clear Modular Workflows (Priority: P1)

**Goal**: Refactor the current root-level trading flow into explicit, understandable modules without changing core behavior

**Independent Test**: A developer can trace the decision pipeline through config, data/news, sentiment, strategy, risk, execution, and app modules without touching unrelated files

### Tests for User Story 1

- [x] T014 [P] [US1] Add unit coverage for extracted signal decision helpers in `tests/unit/test_signal_logic.py`
- [x] T015 [P] [US1] Add unit coverage for extracted position sizing helpers in `tests/unit/test_position_sizing.py`

### Implementation for User Story 1

- [x] T016 [P] [US1] Move configuration model and loader logic from `config.py` into `tradingbot/config/settings.py`
- [x] T017 [P] [US1] Move news/data access logic from `data_handler.py` into `tradingbot/data/news.py`
- [x] T018 [P] [US1] Move sentiment scoring helpers from `finbert_utils.py` into `tradingbot/sentiment/scoring.py`
- [x] T019 [P] [US1] Move risk dataclasses and calculations from `portfolio.py` into `tradingbot/risk/sizing.py`
- [x] T020 [US1] Extract pure signal-generation helpers from `strategy.py` into `tradingbot/strategy/signals.py`
- [x] T021 [US1] Rebuild the Lumibot strategy adapter in `tradingbot/strategy/lumibot_strategy.py` using the new config, data, sentiment, and risk modules
- [x] T022 [US1] Update legacy compatibility imports in `config.py`, `data_handler.py`, `finbert_utils.py`, `portfolio.py`, and `strategy.py` to point at the new package modules

**Checkpoint**: The codebase is modularized into the requested functional areas and can be reasoned about as separate components

---

## Phase 4: User Story 2 - Run Paper Trading Safely With Configurable Multi-Asset Settings (Priority: P2)

**Goal**: Enable configurable paper trading across stock and crypto instruments using the modular runtime

**Independent Test**: An operator can set environment-driven symbols and risk settings, run in paper mode, and get logged decisions without triggering live execution

### Tests for User Story 2

- [x] T023 [P] [US2] Extend paper-mode guardrail smoke coverage for multi-asset settings in `tests/smoke/test_paper_mode_guardrails.py`

### Implementation for User Story 2

- [x] T024 [P] [US2] Add multi-symbol and asset-class configuration parsing in `tradingbot/config/settings.py`
- [x] T025 [P] [US2] Implement paper-mode execution runtime in `tradingbot/app/live.py`
- [x] T026 [US2] Update `tradingbot/execution/broker.py` to build Alpaca paper broker sessions from environment variables only
- [x] T027 [US2] Update `tradingbot/strategy/lumibot_strategy.py` to evaluate configured stock and crypto instruments within one workflow
- [x] T028 [US2] Update decision and fill log schema handling for mode and asset class in `tradingbot/execution/logging.py`
- [x] T029 [US2] Update operator dashboard parsing for paper-mode multi-asset visibility in `monitor_app.py`

**Checkpoint**: Paper trading works with configurable stock/crypto settings and operator-visible logs

---

## Phase 5: User Story 3 - Enable Controlled Live Multi-Asset Trading (Priority: P3)

**Goal**: Allow autonomous live trading only after the explicit two-step live gate passes

**Independent Test**: Live mode refuses to start unless both live-enable conditions are met, then runs autonomously with the same strategy and risk controls as paper mode

### Tests for User Story 3

- [ ] T030 [P] [US3] Add smoke scenarios for missing persistent live flag and missing per-run confirmation in `tests/smoke/test_paper_mode_guardrails.py`

### Implementation for User Story 3

- [ ] T031 [P] [US3] Add live-mode credential and safeguard validation in `tradingbot/execution/safeguards.py`
- [ ] T032 [P] [US3] Add Alpaca live broker construction path in `tradingbot/execution/broker.py`
- [ ] T033 [US3] Implement guarded live runtime entrypoint in `tradingbot/app/live.py`
- [ ] T034 [US3] Update `tradingbot/app/main.py` to enforce the two-step live gate before live execution
- [ ] T035 [US3] Record explicit blocked-live and active-live events in `tradingbot/execution/logging.py`
- [ ] T036 [US3] Update `monitor_app.py` to surface blocked-live versus active-live status clearly

**Checkpoint**: Live trading is autonomous after explicit enablement, but accidental live execution remains blocked

---

## Phase 6: User Story 4 - Backtest and Review Multi-Asset Strategy Behavior (Priority: P4)

**Goal**: Preserve and improve backtesting plus operator review for the modular multi-asset strategy

**Independent Test**: A user can run a backtest with the modular pipeline and review decisions, outcomes, and guardrail effects for configured instruments

### Tests for User Story 4

- [ ] T037 [P] [US4] Extend backtest smoke coverage for modular app routing in `tests/smoke/test_backtest_entrypoint.py`

### Implementation for User Story 4

- [ ] T038 [P] [US4] Implement backtest runtime entrypoint in `tradingbot/app/backtest.py`
- [ ] T039 [P] [US4] Update `backtester.py` to delegate through `tradingbot/app/backtest.py`
- [ ] T040 [US4] Ensure signal, risk, and logging modules are reused in backtest mode from `tradingbot/strategy/signals.py`, `tradingbot/risk/sizing.py`, and `tradingbot/execution/logging.py`
- [ ] T041 [US4] Update decision and snapshot outputs for backtest review in `tradingbot/execution/logging.py`
- [ ] T042 [US4] Refresh operator review guidance in `specs/002-modular-trading-bot/quickstart.md`

**Checkpoint**: Backtesting reuses the modular trading flow and produces reviewable operator evidence

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Finalize migration quality, runtime checks, and documentation

- [ ] T043 [P] Verify all credentials and mode switches are environment-variable driven in `tradingbot/config/settings.py`, `tradingbot/execution/safeguards.py`, and `tradingbot/app/main.py`
- [ ] T044 [P] Run and stabilize `pytest` suites in `tests/unit/test_signal_logic.py`, `tests/unit/test_position_sizing.py`, `tests/smoke/test_backtest_entrypoint.py`, and `tests/smoke/test_paper_mode_guardrails.py`
- [ ] T045 Measure startup and daily trading runtime against the plan targets and record results in `specs/002-modular-trading-bot/quickstart.md`
- [ ] T046 Remove obsolete root-level logic after compatibility delegation is proven in `config.py`, `data_handler.py`, `finbert_utils.py`, `portfolio.py`, `strategy.py`, `backtester.py`, and `tradingbot.py`
- [ ] T047 Validate dashboard/log outputs against the contract in `specs/002-modular-trading-bot/contracts/cli-contract.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on User Story 1 modular extraction and Foundational completion
- **User Story 3 (Phase 5)**: Depends on User Story 2 paper-mode execution path and Foundational completion
- **User Story 4 (Phase 6)**: Depends on User Story 1 modular extraction and Foundational completion
- **Polish (Final Phase)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Establishes the modular package boundaries and should be treated as the MVP foundation
- **User Story 2 (P2)**: Depends on modular runtime plus shared config/execution guardrails
- **User Story 3 (P3)**: Depends on the shared execution runtime and should reuse the paper-mode flow rather than diverge from it
- **User Story 4 (P4)**: Depends on the shared modular signal/risk/runtime layers but can progress in parallel with some live-mode work after US1

### Within Each User Story

- Tests should be written or updated before finalizing the implementation slice
- Config and pure domain helpers precede runtime adapters
- Runtime adapters precede dashboard or documentation adjustments
- Story-specific logging and validation must land before the story is considered complete

### Parallel Opportunities

- T002, T003, and T004 can run in parallel
- T006, T007, and T008 can run in parallel after T005 starts the shared structure
- T016, T017, T018, and T019 can run in parallel
- T024 and T025 can run in parallel once foundational config/execution primitives are ready
- T031 and T032 can run in parallel
- T038 and T039 can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Move configuration model and loader logic from config.py into tradingbot/config/settings.py"
Task: "Move news/data access logic from data_handler.py into tradingbot/data/news.py"
Task: "Move sentiment scoring helpers from finbert_utils.py into tradingbot/sentiment/scoring.py"
Task: "Move risk dataclasses and calculations from portfolio.py into tradingbot/risk/sizing.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. Validate the modular package and unit tests for signal logic and sizing
5. Stop and confirm the new module layout before expanding runtime behaviors

### Incremental Delivery

1. Build the modular package foundation
2. Add multi-asset paper trading and validate logs/dashboard behavior
3. Add guarded live trading on top of the shared runtime
4. Reconnect and validate backtesting with the same modular pipeline
5. Finish with performance verification and cleanup

### Parallel Team Strategy

With multiple developers:

1. One developer owns config/execution foundations
2. One developer owns strategy/sentiment/risk extraction
3. One developer owns tests and monitoring updates
4. Merge on the shared package boundaries after Phase 2

---

## Notes

- [P] tasks target different files with minimal overlap
- Story labels map directly to the prioritized spec user stories
- User Story 1 is the recommended MVP because it unlocks every later slice
- All stories must preserve fail-closed live behavior and operator-visible decision logging
- Tasks are written to be directly actionable by an implementation agent without extra planning context
