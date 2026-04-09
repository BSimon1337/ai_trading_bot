# Feature Specification: Modular Multi-Asset Trading Bot

**Feature Branch**: `002-modular-trading-bot`  
**Created**: 2026-04-08  
**Status**: Draft  
**Input**: User description: "Refactor the trading bot into modular components for configuration, sentiment ingestion, signal generation, risk management, execution, and backtesting. The system must support paper trading with Alpaca, historical backtesting, and configurable symbol/risk settings. It must prevent accidental live execution and log all trade decisions."

## Clarifications

### Session 2026-04-08

- Q: What live-trading safeguard should gate real-money execution? -> A: Two-step gate with persistent enable setting plus per-run confirmation check.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the Bot Through Clear Modular Workflows (Priority: P1)

As an operator or developer, I want the trading bot split into clear functional modules so that
configuration, data-driven decisions, execution, monitoring, and backtesting can be understood,
changed, and run without hidden coupling.

**Why this priority**: Modular structure is the foundation for every other requested behavior.
Without it, paper trading, controlled live trading, multi-asset strategy changes, and safety controls
remain harder to reason about and maintain.

**Independent Test**: A user can identify and use distinct flows for configuration, sentiment input,
signal generation, risk controls, execution, monitoring, and backtesting without needing to modify
unrelated parts of the system.

**Acceptance Scenarios**:

1. **Given** the user wants to adjust one area of the bot, **When** they work within the relevant
   functional area, **Then** they can do so without changing unrelated system behavior.
2. **Given** the user needs to understand how a trade decision is produced, **When** they review the
   system workflow, **Then** they can trace the decision through the distinct functional stages.

---

### User Story 2 - Run Paper Trading Safely With Configurable Multi-Asset Settings (Priority: P2)

As an operator, I want to run the bot in paper trading with configurable stock and crypto symbols and
risk limits so that I can validate behavior in a realistic environment without using live funds.

**Why this priority**: Paper trading is the primary validation mode and the safest path for testing the
combined modular and multi-asset behavior before live use.

**Independent Test**: The operator can configure eligible stock and crypto symbols plus risk settings,
start a paper-trading run, and observe decisions and simulated executions without triggering live trading.

**Acceptance Scenarios**:

1. **Given** the operator provides supported symbol and risk settings, **When** they start a paper run,
   **Then** the system uses those settings and runs in paper mode.
2. **Given** eligible stock and crypto instruments are configured, **When** opportunities are evaluated,
   **Then** the system can produce decisions for either asset class under one operating workflow.

---

### User Story 3 - Enable Controlled Live Multi-Asset Trading (Priority: P3)

As an operator, I want to intentionally enable live trading only after explicit confirmation and
safeguard checks so that the bot can place real-money trades autonomously without accidental activation.

**Why this priority**: Live trading is a direct goal, but it is higher risk than modular refactoring
and paper validation, so it must follow clear guardrails.

**Independent Test**: The bot remains blocked from live execution by default, then enters live execution
only when the required opt-in and safeguards are satisfied, after which it can submit trades without
per-trade operator approval.

**Acceptance Scenarios**:

1. **Given** live trading has not been explicitly enabled, **When** the operator starts a live run,
   **Then** the system refuses to place real-money trades and explains what is missing.
2. **Given** live trading has been explicitly enabled and all safety conditions are met,
   **When** the operator starts a live run, **Then** the system proceeds with autonomous live execution
   and records that live mode is active.

---

### User Story 4 - Backtest and Review Multi-Asset Strategy Behavior (Priority: P4)

As an operator or developer, I want to run historical backtests and inspect logged decisions so that I
can evaluate strategy behavior, trade pursuit, and guardrail outcomes before or alongside paper and live use.

**Why this priority**: Backtesting and observability are how the operator validates changes and builds
confidence in the strategy across both stock and crypto instruments.

**Independent Test**: A user can run a historical test with configurable settings and review the resulting
decisions, trades, and summaries for each enabled asset class.

**Acceptance Scenarios**:

1. **Given** historical data and configuration inputs are available, **When** the user runs a backtest,
   **Then** the system produces historical results using the same overall decision workflow as operational runs.
2. **Given** paper, live, or backtest activity exists, **When** the operator reviews the outputs,
   **Then** they can inspect recent decisions, fills, execution mode, and blocked trade attempts without
   reading source code.

---

### Edge Cases

- What happens when required configuration values are missing or invalid?
- How does the system behave when sentiment input is unavailable or empty for a decision cycle?
- What happens when a signal is generated but risk controls block execution?
- How does the system behave when paper trading credentials are unavailable or rejected?
- What happens when a user attempts to start live execution without the required explicit opt-in?
- How does the system behave when no qualified opportunities are available in either asset class?
- How does the system behave when one asset class is unavailable while the other remains tradable?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST separate configuration, sentiment ingestion, signal generation, risk management, execution, monitoring, and backtesting into clear functional components.
- **FR-002**: The system MUST allow supported symbol and risk settings to be configured without changing core trading logic.
- **FR-003**: The system MUST support paper trading with Alpaca as an available execution mode.
- **FR-004**: The system MUST support historical backtesting using the same overall decision workflow as operational trading runs.
- **FR-005**: The system MUST support opportunity evaluation for both stock and crypto instruments within a unified operating workflow.
- **FR-006**: The system MUST allow operators to configure which stock and crypto instruments are eligible for trading.
- **FR-007**: The system MUST apply risk-management controls before any trade is executed in paper or live-capable workflows.
- **FR-008**: The system MUST prevent accidental live execution by keeping live trading disabled unless an explicit live-trading opt-in is provided.
- **FR-008a**: The live-trading opt-in MUST use a two-step gate composed of a persistent live-enable setting and a separate per-run confirmation check before any live order submission is allowed.
- **FR-009**: The system MUST permit autonomous trade submission after live trading is intentionally enabled and safeguards are satisfied.
- **FR-010**: The system MUST clearly indicate whether a run is executing in backtest mode, paper mode, live mode, or blocked live mode.
- **FR-011**: The system MUST log every trade decision, including decisions that result in no trade or a blocked trade.
- **FR-012**: The system MUST preserve enough decision context for an operator to understand why a trade was taken, skipped, or rejected.
- **FR-013**: The system MUST record operator-visible evidence of recent decisions, executed trades, and blocked trade attempts.
- **FR-014**: The system MUST continue operating safely when one asset class is temporarily unavailable, including skipping or deferring only the affected opportunities.
- **FR-015**: The system MUST fail safely when inputs, credentials, or dependencies required for a trading run are unavailable.

### Key Entities *(include if feature involves data)*

- **Run Configuration**: The collection of operator-defined settings that control symbols, risk parameters, trading mode, and evaluation scope.
- **Eligible Instrument**: A stock or crypto instrument approved for evaluation and possible trading under the current configuration.
- **Sentiment Input**: The information gathered for strategy evaluation that influences the trading decision.
- **Trading Signal**: The output of the decision stage that represents whether the system sees a qualified opportunity.
- **Risk Decision**: The result of applying risk rules to a proposed trade, including allow, reduce, or block outcomes.
- **Execution Record**: The operator-visible record of what the system decided and what action, if any, followed.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: Current configuration handling, trading runner, strategy flow, risk checks, backtesting flow, log outputs, and monitoring dashboard patterns.
- **Planned deviations**: The main change is structural separation into clearer modules while preserving the current operator workflow where practical.
- **New dependencies**: None assumed at specification time.
- **Operational impact**: This feature affects execution safety, multi-asset opportunity selection, paper-trading runs, live-trading runs, backtesting runs, configuration management, and auditability of decisions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can configure stock and crypto symbols plus risk settings for a paper-trading run in under 10 minutes without modifying core trading logic.
- **SC-002**: In validation runs, 100% of attempted live starts without the explicit opt-in are blocked before any live order can be submitted.
- **SC-002a**: In validation runs, 100% of attempted live starts missing either the persistent live-enable setting or the per-run confirmation check are blocked before any live order can be submitted.
- **SC-003**: After explicit live enablement, the bot can autonomously process and submit qualified trades without requiring per-trade operator approval.
- **SC-004**: In representative paper and backtest runs, the system can produce at least one independently reviewable decision stream for each enabled asset class.
- **SC-005**: In representative paper, live, and backtest runs, 100% of trade decisions are recorded with enough context to explain whether the bot traded, skipped, or blocked the action.
- **SC-006**: A developer can identify the responsible functional area for configuration, sentiment ingestion, signal generation, risk management, execution, monitoring, and backtesting without tracing through unrelated modules.

## Assumptions

- Paper trading with Alpaca remains the primary operational validation mode for this project.
- Historical data access already exists or will be provided through the system's current backtesting workflow.
- The preferred outcome is a modular refactor that preserves established project behaviors unless a justified deviation is needed.
- Preventing accidental live execution means requiring explicit live enablement, not requiring manual approval for each trade once live trading is intentionally enabled.
- Live enablement requires both a persistent setting and a separate per-run confirmation before autonomous live trading can begin.
- Performance optimization in this feature means improving the bot's ability to find and act on qualified opportunities across stocks and crypto, not guaranteeing profitability.
