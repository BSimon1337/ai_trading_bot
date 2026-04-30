# Implementation Plan: Monitor Runtime Observability

**Branch**: `010-monitor-runtime-observability` | **Date**: 2026-04-30 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/010-monitor-runtime-observability/spec.md`

## Summary

Strengthen the monitor so it can be trusted as the operator-visible source of runtime truth for both stock and crypto bots. The implementation will reuse the existing Flask monitor, runtime registry, symbol-scoped CSV evidence, and tray-facing summary model; add a normalized observability layer for runtime events, warnings, and order lifecycle; tighten symbol-by-symbol portfolio-state isolation; and make freshness and provisional-versus-confirmed state explicit in the dashboard instead of forcing the operator to infer what happened from terminal output.

## Observability Scope

- **Runtime truth first**: `tradingbot/app/runtime_manager.py` and its runtime registry remain the authoritative lifecycle source, but the monitor must reconcile them against current process reality on every refresh.
- **Event visibility added**: The monitor will summarize startup milestones, runtime transitions, recent trade lifecycle events, and operator-relevant warnings into one consistent symbol view.
- **Portfolio-state isolation tightened**: Per-symbol held quantity, held value, cash, and provisional fill-delta state must stay symbol-scoped and must not leak across cards during refresh or startup.
- **Shared UX preserved**: Stock and crypto symbols continue through one dashboard model with the same badge semantics, freshness wording, and warning handling.
- **Terminal logs remain fallback**: This phase improves operator visibility but does not attempt to replace the terminal with a developer-grade raw log console.
- **Current architecture preserved**: The plan stays inside the existing Flask/template monitor, tray, runtime registry, and CSV-backed monitor evidence flows.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Flask, pandas, python-dotenv, Lumibot runtime stack, pystray, Pillow, pytest, and the current runtime-manager standard-library stack; no new third-party dependency planned  
**Storage**: Existing symbol-scoped CSV runtime evidence plus the local runtime-registry JSON; observability summaries remain derived views rather than new durable storage systems  
**Testing**: pytest unit, contract, and smoke tests covering runtime reconciliation, symbol-card payload shaping, warning/event visibility, provisional portfolio state, and mixed stock/crypto dashboard rendering  
**Target Platform**: Local Windows desktop first, with Flask/template dashboard on localhost and local managed bot processes  
**Project Type**: Existing Python trading bot with local dashboard/tray monitoring application and app-owned runtime lifecycle backend  
**Performance Goals**: Runtime state, symbol warnings, and recent event changes should appear within the next monitor refresh cycle, and no refresh should cause cross-symbol state corruption  
**Constraints**: Preserve live/paper safety behavior, reuse the current Flask/template architecture, avoid new dependencies, avoid introducing a separate backend or database, keep the tray aligned with dashboard truth, and keep symbol state isolated even during startup races and stale-evidence edge cases  
**Scale/Scope**: Small local mixed symbol set, one operator, one local monitor session, runtime evidence from a handful of stock and crypto bots, and one normalized observability model shared across all symbol cards

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: The plan extends the existing Flask monitor, tray summary path, runtime registry reconciliation, and CSV evidence readers instead of introducing a new frontend stack, event service, or external datastore.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: This feature improves observability only and must not bypass or weaken live-trading safeguards, runtime-manager controls, or fail-closed behavior.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: No new dependencies are planned.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Validation will include unit tests for event normalization, warning extraction, runtime reconciliation, and portfolio-state isolation; contract tests for monitor payload fields; smoke tests for the live monitor entrypoint; and manual dashboard-to-log verification during mixed-symbol startup and fill scenarios.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence will include reconciled runtime state, per-symbol recent event summaries, warning visibility, provisional/confirmed portfolio labels, badge consistency across stock and crypto cards, and continued symbol-scoped CSV/log outputs that match what the dashboard reports.

## Project Structure

### Documentation (this feature)

```text
specs/010-monitor-runtime-observability/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- dashboard-runtime-events-contract.md
|   `-- monitor-runtime-observability-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- monitor.py
|   |-- monitor_app.py
|   |-- runtime_manager.py
|   `-- tray.py
|-- config/
|   `-- settings.py
`-- strategy/
    `-- lumibot_strategy.py

templates/
`-- monitor.html

tests/
|-- contract/
|   |-- test_dashboard_monitor_contract.py
|   `-- test_tray_monitor_contract.py
|-- smoke/
|   |-- test_monitor_entrypoint.py
|   `-- test_runtime_manager_entrypoint.py
`-- unit/
    |-- test_monitor_data.py
    |-- test_runtime_manager.py
    `-- test_tray_state.py
```

**Structure Decision**: Reuse the existing Flask monitor and runtime-manager stack, with `monitor.py` as the main observability aggregator, `runtime_manager.py` as runtime truth and reconciliation source, and `monitor.html`/`tray.py` as the operator-facing renderers of the same normalized status model.

## Observability Evidence Strategy

- **Runtime truth evidence**: Every symbol card must reflect reconciled managed runtime state, not stale startup assumptions or orphaned process metadata.
- **Event evidence**: Each symbol must expose a recent runtime/event summary that lets an operator see startup, readiness, iteration, and trade-lifecycle progress without reading terminal output.
- **Warning evidence**: Broker anomalies, malformed evidence conditions, and runtime-specific warnings must surface on the relevant symbol card in readable operator language.
- **Portfolio-state evidence**: Held quantity, held value, and cash must declare whether they come from confirmed snapshot evidence or provisional fill-based reconstruction.
- **Isolation evidence**: Mixed-symbol dashboard validation must prove that one symbol's state cannot overwrite another symbol's values during startup, refresh, or delayed snapshot scenarios.
- **Cross-surface consistency evidence**: The tray, dashboard summary, and per-symbol cards must agree on live/paper state and major runtime outcomes.

## Phase 0: Research

### Research Questions

1. What is the safest way to normalize runtime milestones, warnings, and order-lifecycle state from the existing runtime registry and symbol-scoped CSV evidence without adding a new event store?
2. How should the monitor derive effective per-symbol portfolio state when fills are newer than snapshots, while preventing cross-symbol leakage and preserving account-level context?
3. What operator-facing wording and badge precedence should be used so live/paper context, provisional data, stale data, and failure conditions remain consistent across stock and crypto cards?

### Research Decisions (resolved)

See [research.md](./research.md).

## Phase 1: Design & Contracts

### Design Outputs

- **Data model**: Define the normalized runtime event, order-lifecycle, warning, effective portfolio-state, and freshness entities the monitor will derive for each symbol.
- **Contracts**: Define the monitor payload additions for runtime events, warnings, provisional-state labeling, and badge/freshness semantics, plus the dashboard event-feed behavior contract.
- **Quickstart**: Define how to validate reconciled runtime truth, warning visibility, order lifecycle, and symbol-state isolation in a mixed stock-and-crypto live or paper monitor session.
- **Agent context**: Refresh repo agent context so the new observability work is reflected in the project metadata.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: the design stays inside the current Flask monitor, tray, runtime registry, and symbol-scoped CSV evidence architecture.
- Trading safety remains satisfied: improved observability increases operator confidence without weakening live-mode guardrails or order-path protections.
- Dependency discipline remains satisfied: the plan adds no new third-party packages and relies on the existing Python stack.
- Validation remains proportional: runtime reconciliation, event/warning visibility, and symbol-state isolation will be covered by unit, contract, smoke, and mixed-symbol manual verification.
- Observable operations remain strongly satisfied: runtime state, event summaries, warnings, provisional portfolio labels, and cross-symbol consistency become first-class operator-visible outputs rather than implicit side effects.
