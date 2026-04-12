# Feature Specification: Preflight Validation and Offline Development Mode

**Feature Branch**: `004-preflight-offline-mode`  
**Created**: 2026-04-11  
**Status**: Draft  
**Input**: User description: "Add a preflight validation command and offline development mode. The system should verify Alpaca trading credentials, Alpaca market data/news access, model loadability, dependency availability, log paths, paper/live safeguards, and symbol configuration before running. It should also support cached/local news fixtures so backtests can run meaningfully when Alpaca News is unavailable."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Validate Readiness Before Running (Priority: P1)

As an operator preparing to run the bot, I want a single readiness check that tells me whether credentials, market data access, model availability, symbol configuration, log paths, and paper/live safeguards are valid before I start trading or backtesting.

**Why this priority**: This prevents confusing runtime failures and helps the operator identify unsafe or incomplete configuration before the bot starts.

**Independent Test**: Can be fully tested by running the readiness check with valid and invalid configuration and confirming the resulting status clearly identifies pass, warning, and fail conditions.

**Acceptance Scenarios**:

1. **Given** complete paper-trading configuration and accessible dependencies, **When** the operator runs the readiness check, **Then** the system reports all required checks as passing and marks the runtime safe to start.
2. **Given** missing or unauthorized Alpaca News access, **When** the operator runs the readiness check, **Then** the system reports the issue as a warning for backtesting and a clear blocker only for flows that require live news access.
3. **Given** live trading is requested without the required live safeguards, **When** the operator runs the readiness check, **Then** the system reports live trading as blocked and explains which safeguard is missing.

---

### User Story 2 - Backtest While External News Is Unavailable (Priority: P2)

As a developer working without working Alpaca News access, I want an offline development mode that uses cached or local news inputs so backtests can still exercise sentiment-driven behavior instead of always falling back to neutral sentiment.

**Why this priority**: This keeps strategy development productive while account access or third-party services are unavailable.

**Independent Test**: Can be tested by disabling Alpaca News access, providing local news fixtures for configured symbols, and confirming that backtests use the local inputs and produce decision evidence.

**Acceptance Scenarios**:

1. **Given** local news fixtures exist for the configured symbol and date range, **When** the operator runs a backtest in offline development mode, **Then** the system uses the local fixture data and records that the news source was offline/local.
2. **Given** local news fixtures are missing for part of the requested date range, **When** the backtest runs in offline development mode, **Then** the system reports the fixture gap and falls back to neutral sentiment only for the missing intervals.
3. **Given** Alpaca News access works, **When** offline development mode is not enabled, **Then** the system continues to use the normal external news source.

---

### User Story 3 - Diagnose Optional Model and Dependency Gaps (Priority: P3)

As a developer or operator, I want the readiness check to distinguish required runtime dependencies from optional model or local sentiment dependencies so I know whether the bot can still run safely with fallbacks.

**Why this priority**: Optional model and sentiment packages are useful but heavy; the operator should know when they are missing without confusing that with a full runtime failure.

**Independent Test**: Can be tested by running the readiness check with the saved model present but model dependencies missing, then confirming the report explains the fallback behavior and whether the run remains allowed.

**Acceptance Scenarios**:

1. **Given** the saved model exists but cannot be loaded because optional model dependencies are missing, **When** the readiness check runs, **Then** the system reports a warning and explains that model signals will be disabled for that run.
2. **Given** local sentiment dependencies are not installed, **When** the readiness check runs, **Then** the system reports whether sentiment can be estimated from available sources or must fall back to neutral behavior.
3. **Given** a required runtime dependency is missing, **When** the readiness check runs, **Then** the system reports a failure and advises the operator not to start the bot.

### Edge Cases

- Alpaca trading credentials are valid but Alpaca market data or news access is unauthorized.
- The configured symbols include both stocks and crypto assets with different trading schedules and data availability.
- Offline news fixtures are present but malformed, stale, empty, or outside the requested backtest date range.
- Log directories are missing, read-only, or point to locations that cannot be created.
- Live trading is requested while paper mode is still enabled, or live safeguards are incomplete.
- A saved model file exists but cannot be loaded because a dependency is missing or the file is incompatible.
- Dependency checks run on a clean install where optional packages are intentionally absent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single operator-invoked readiness check before trading or backtesting that summarizes runtime readiness.
- **FR-002**: System MUST verify that required credentials are present and that Alpaca trading access, market data access, and news access are reported separately.
- **FR-003**: System MUST verify configured symbols and classify each as stock or crypto with operator-visible results.
- **FR-004**: System MUST verify paper/live mode safeguards and block live readiness when required live safeguards are not satisfied.
- **FR-005**: System MUST verify that decision, fill, and snapshot log destinations are writable or can be created before runtime starts.
- **FR-006**: System MUST verify whether the saved model can be loaded and report model-signal availability separately from overall runtime availability.
- **FR-007**: System MUST verify required dependencies separately from optional model and local sentiment dependencies.
- **FR-008**: System MUST support an offline development mode for backtests that uses cached or local news inputs when external news access is unavailable.
- **FR-009**: System MUST record whether each backtest decision used external news, cached/local news, or neutral fallback sentiment.
- **FR-010**: System MUST report fixture gaps, malformed fixture data, and neutral fallback usage in an operator-visible way without crashing the backtest.
- **FR-011**: System MUST return an overall readiness outcome of pass, warning, or fail, with individual check details and actionable remediation text.
- **FR-012**: System MUST preserve existing fail-closed live trading behavior regardless of offline development mode.

### Key Entities *(include if feature involves data)*

- **Readiness Check Result**: Represents the outcome of a single validation item, including check name, status, affected area, message, and recommended action.
- **Readiness Report**: Represents the full pre-run validation summary, including overall status, individual check results, timestamp, mode, and configured symbols.
- **Offline News Fixture**: Represents local or cached news input for a symbol and date range, including headline text, source label, timestamp, and validation state.
- **Data Source Status**: Represents whether external news, cached/local news, or neutral fallback is available for a given run.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: Existing configuration loading, paper/live guardrails, modular data/news ingestion, sentiment fallback behavior, model loading fallback, decision logging, backtest entrypoint, quickstart documentation, and dashboard-compatible log patterns.
- **Planned deviations**: The readiness check introduces a deliberate pre-run validation flow so operators can diagnose issues before starting runtime, rather than discovering them only after the bot begins backtesting or trading.
- **New dependencies**: None assumed for the base feature. Optional model and local sentiment dependencies remain optional and must be pinned exactly if later enabled.
- **Operational impact**: Operators will see a pre-run readiness summary, backtest logs will identify external versus local versus neutral sentiment sources, and live trading will remain blocked unless all existing live safeguards are satisfied.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can identify whether the bot is ready to run in under 30 seconds after starting the readiness check.
- **SC-002**: The readiness report distinguishes credential, data access, model, dependency, log path, symbol, and live safeguard issues with 100% of checks assigned pass, warning, or fail status.
- **SC-003**: Backtests using offline development mode complete without crashing when external news access is unavailable, provided local fixtures exist for at least one configured symbol and date range.
- **SC-004**: When local fixture coverage is incomplete, the system reports each missing coverage interval and continues with neutral fallback for those intervals.
- **SC-005**: Live readiness is reported as failed whenever required live safeguards are incomplete, even if offline development mode is enabled.
- **SC-006**: Decision evidence shows the sentiment data source for each evaluated decision so an operator can audit whether external, local, or neutral fallback data was used.

## Assumptions

- Offline development mode is intended for backtesting and local validation, not as a way to bypass live-trading safeguards.
- Missing Alpaca News access should be a warning for offline-capable backtests but a visible operational issue for production trading readiness.
- Local news fixtures can be maintained manually or generated by future tooling; this feature only requires the system to consume and validate them.
- Optional model and local sentiment dependencies may remain absent during normal development, as long as the system reports the resulting fallback clearly.
- Existing CSV decision and runtime logs remain the primary operator-visible evidence unless a later feature expands the dashboard.
