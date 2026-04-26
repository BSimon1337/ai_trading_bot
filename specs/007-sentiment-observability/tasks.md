# Tasks: Sentiment Observability

**Input**: Design documents from `/specs/007-sentiment-observability/`  
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks are included because the plan requires pytest unit, contract, and smoke validation for sentiment payload shaping, fallback-state handling, headline preview behavior, and dashboard rendering.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Prepare the sentiment-observability feature scaffolding and document the reused runtime evidence path.

- [x] T001 Document the reused sentiment/news/monitor evidence path in `specs/007-sentiment-observability/plan.md`
- [x] T002 [P] Refresh sentiment fixture notes and sample monitor scenarios in `tests/fixtures/monitor/README.md`
- [x] T003 [P] Review the dashboard payload contract additions needed for sentiment visibility in `specs/007-sentiment-observability/contracts/dashboard-monitor-contract.md`

---

## Phase 2: Foundational

**Purpose**: Establish shared sentiment evidence structures before any story-specific UI work begins.

**Critical**: No user story work should start until sentiment evidence capture and monitor parsing rules are in place.

- [x] T004 Implement shared sentiment snapshot and availability helpers in `tradingbot/app/monitor.py`
- [x] T005 Implement bounded headline-preview and sentiment-trend helper structures in `tradingbot/app/monitor.py`
- [x] T006 Add or extend strategy/runtime sentiment evidence capture in `tradingbot/strategy/lumibot_strategy.py`
- [x] T007 [P] Extend news-source metadata support for bounded headline evidence in `tradingbot/data/news.py`
- [x] T008 [P] Add foundational sentiment fixture builders or fixture coverage in `tests/unit/test_monitor_data.py`
- [x] T009 [P] Add foundational unit tests for sentiment snapshot parsing, fallback-state classification, and headline bounding in `tests/unit/test_monitor_data.py`

**Checkpoint**: Shared sentiment evidence logic is ready for story-specific monitor rendering.

---

## Phase 3: User Story 1 - See Current Sentiment State Per Bot (Priority: P1) 🎯 MVP

**Goal**: Show the latest sentiment label, confidence, source, and fallback state per monitored symbol.

**Independent Test**: Load symbols with current sentiment activity and fallback-only sentiment activity, then confirm each instance exposes the latest sentiment state without breaking current monitor behavior.

### Tests for User Story 1

- [x] T010 [P] [US1] Add unit tests for current per-symbol sentiment snapshot extraction in `tests/unit/test_monitor_data.py`
- [x] T011 [P] [US1] Add unit tests for fallback-neutral versus real-neutral sentiment state handling in `tests/unit/test_monitor_data.py`
- [x] T012 [P] [US1] Add contract tests for per-instance sentiment payload fields in `tests/contract/test_dashboard_monitor_contract.py`

### Implementation for User Story 1

- [x] T013 [US1] Extend sentiment scoring outputs to expose operator-readable availability state in `tradingbot/sentiment/scoring.py`
- [x] T014 [US1] Capture current sentiment snapshot fields in runtime evidence from `tradingbot/strategy/lumibot_strategy.py`
- [x] T015 [US1] Add per-instance sentiment payload shaping in `tradingbot/app/monitor.py`
- [x] T016 [US1] Update summary cards and detail cards to show current sentiment state in `templates/monitor.html`
- [x] T017 [US1] Validate User Story 1 by running `tests/unit/test_monitor_data.py` and `tests/contract/test_dashboard_monitor_contract.py`

**Checkpoint**: The monitor shows trustworthy current sentiment state per symbol.

---

## Phase 4: User Story 2 - Understand the News Behind Sentiment (Priority: P2)

**Goal**: Show bounded headline evidence, headline counts, and recent sentiment trend per monitored symbol.

**Independent Test**: Load symbols with multiple recent headlines and changing sentiment observations, then confirm the dashboard shows bounded headline previews and recent sentiment history without requiring raw log inspection.

### Tests for User Story 2

- [ ] T018 [P] [US2] Add unit tests for bounded headline-preview extraction in `tests/unit/test_monitor_data.py`
- [ ] T019 [P] [US2] Add unit tests for recent sentiment trend assembly in `tests/unit/test_monitor_data.py`
- [ ] T020 [P] [US2] Add contract tests for `headline_count`, `headline_preview`, and `sentiment_trend` fields in `tests/contract/test_dashboard_monitor_contract.py`

### Implementation for User Story 2

- [ ] T021 [US2] Extend news evidence capture to retain bounded recent headline context in `tradingbot/data/news.py`
- [ ] T022 [US2] Persist or assemble recent sentiment trend evidence in `tradingbot/strategy/lumibot_strategy.py`
- [ ] T023 [US2] Add headline-preview and sentiment-trend aggregation in `tradingbot/app/monitor.py`
- [ ] T024 [US2] Update sentiment detail rendering and bounded headline sections in `templates/monitor.html`
- [ ] T025 [US2] Validate User Story 2 by running `tests/unit/test_monitor_data.py` and `tests/contract/test_dashboard_monitor_contract.py`

**Checkpoint**: Operators can see the news context and recent sentiment direction behind each symbol’s state.

---

## Phase 5: User Story 3 - Keep Sentiment Visibility Safe and Explainable (Priority: P3)

**Goal**: Keep sentiment context bounded, readable, stale-aware, and safely read-only during live monitoring.

**Independent Test**: Load current, stale, and fallback sentiment evidence together, then confirm the dashboard marks stale sentiment appropriately, bounds previews safely, and preserves read-only behavior.

### Tests for User Story 3

- [ ] T026 [P] [US3] Add unit tests for stale-sentiment visibility and no-headline state handling in `tests/unit/test_monitor_data.py`
- [ ] T027 [P] [US3] Add contract tests for sentiment availability and stale-state rendering in `tests/contract/test_dashboard_monitor_contract.py`
- [ ] T028 [P] [US3] Add smoke coverage for monitor startup with mixed sentiment and fallback evidence in `tests/smoke/test_monitor_entrypoint.py`

### Implementation for User Story 3

- [ ] T029 [US3] Implement stale-sentiment classification and bounded fallback messaging in `tradingbot/app/monitor.py`
- [ ] T030 [US3] Update dashboard wording and sentiment visual cues for stale or unavailable evidence in `templates/monitor.html`
- [ ] T031 [US3] Confirm tray and monitor remain read-only with sentiment additions in `tradingbot/app/tray.py`
- [ ] T032 [US3] Document sentiment observability operating guidance and manual validation in `specs/007-sentiment-observability/quickstart.md`
- [ ] T033 [US3] Validate User Story 3 by running `tests/unit/test_monitor_data.py`, `tests/contract/test_dashboard_monitor_contract.py`, and `tests/smoke/test_monitor_entrypoint.py`

**Checkpoint**: Sentiment visibility remains explainable, bounded, and safe during live monitoring.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, operator documentation, and cross-feature validation.

- [ ] T034 [P] Review sentiment field naming for consistency across `tradingbot/app/monitor.py`, `tradingbot/strategy/lumibot_strategy.py`, and `templates/monitor.html`
- [ ] T035 [P] Update operator-facing dashboard notes for sentiment interpretation and fallback behavior in `README.md`
- [ ] T036 [P] Confirm no new dependency or control-plane behavior was introduced in `specs/007-sentiment-observability/research.md` and `tradingbot/app/tray.py`
- [ ] T037 Run full sentiment-monitor validation from `specs/007-sentiment-observability/quickstart.md`
- [ ] T038 Record manual validation notes for FinBERT, fallback, and headline-preview scenarios in `specs/007-sentiment-observability/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP
- **User Story 2 (Phase 4)**: Depends on Foundational and builds on the current sentiment snapshot from US1
- **User Story 3 (Phase 5)**: Depends on Foundational and benefits from the sentiment payload semantics introduced in US1 and US2
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **US1 See Current Sentiment State Per Bot**: Can start after Foundational; no dependency on later stories
- **US2 Understand the News Behind Sentiment**: Can start after Foundational, but should reuse the snapshot fields introduced in US1
- **US3 Keep Sentiment Visibility Safe and Explainable**: Can start after Foundational, with best results once US1 and US2 sentiment payloads exist

### Parallel Opportunities

- Setup tasks T002-T003 can run in parallel
- Foundational tasks T007-T009 can run in parallel after helper design begins
- US1 tests T010-T012 can run in parallel
- US2 tests T018-T020 can run in parallel
- US3 tests T026-T028 can run in parallel
- Polish docs and consistency tasks T034-T036 can run in parallel

---

## Parallel Example: User Story 1

```text
Task: "Add unit tests for current per-symbol sentiment snapshot extraction in tests/unit/test_monitor_data.py"
Task: "Add unit tests for fallback-neutral versus real-neutral sentiment state handling in tests/unit/test_monitor_data.py"
Task: "Add contract tests for per-instance sentiment payload fields in tests/contract/test_dashboard_monitor_contract.py"
```

## Parallel Example: User Story 2

```text
Task: "Add unit tests for bounded headline-preview extraction in tests/unit/test_monitor_data.py"
Task: "Add unit tests for recent sentiment trend assembly in tests/unit/test_monitor_data.py"
Task: "Add contract tests for headline_count, headline_preview, and sentiment_trend fields in tests/contract/test_dashboard_monitor_contract.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 only.
3. Validate that current sentiment label, confidence, source, and fallback state behave correctly.
4. Stop and verify the monitor can explain the latest sentiment state before layering headline previews and trend context.

### Incremental Delivery

1. Deliver US1 current sentiment visibility.
2. Add US2 headline evidence and sentiment-trend context.
3. Add US3 stale/fallback safety and bounded explanation behavior.
4. Run full validation and update operator documentation.

### Safety Notes

- Keep the monitor and tray strictly read-only.
- Do not introduce order placement, strategy tuning, or runtime-control behavior in this feature.
- Preserve current trading decision logic; this feature should expose sentiment behavior, not redefine it.
