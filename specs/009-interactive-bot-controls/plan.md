# Implementation Plan: Interactive Bot Controls

**Branch**: `009-interactive-bot-controls` | **Date**: 2026-04-28 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/009-interactive-bot-controls/spec.md`

## Summary

Add interactive dashboard controls on top of the completed runtime-manager backend so a local operator can start, stop, and restart managed bot runtimes from the monitor itself. The implementation will reuse the existing Flask monitor, runtime registry, runtime-manager lifecycle commands, and dashboard/tray state model; add a safe control request path with live confirmation handling; surface control availability and recent control activity in the monitor; and keep both stock and crypto managed symbols in scope from the first release.

## Control Scope

- **UI surface extended**: The existing Flask dashboard becomes the primary control surface for runtime lifecycle actions.
- **Backend lifecycle reused**: `tradingbot/app/runtime_manager.py` remains the authoritative executor for start, stop, and restart behavior.
- **State source reused**: The runtime registry remains the source of truth for current runtime state and will be extended to retain recent control activity.
- **Asset coverage preserved**: Existing symbol parsing and per-symbol runtime flows continue to support both stock and crypto symbols through one shared control path.
- **Current runtime commands preserved**: Existing CLI/runtime-manager entrypoints remain available as fallback and validation tools while the dashboard becomes the preferred operator path.
- **Tray posture preserved**: The tray remains status-focused in this phase; it may reflect control results but will not become the primary action surface.
- **Live-safety preserved**: Interactive controls must not create a new backdoor around existing live-trading safeguards or confirmation expectations.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Flask, pandas, python-dotenv, Lumibot runtime stack, pystray, Pillow, pytest, and the current runtime-manager standard-library stack; no new third-party dependency planned  
**Storage**: Existing symbol-scoped CSV runtime evidence plus the local runtime-registry JSON extended with recent control activity metadata  
**Testing**: pytest unit, contract, and smoke tests covering control availability, live-confirmation flow, runtime-manager integration, monitor payload shaping, and dashboard action behavior  
**Target Platform**: Local Windows desktop first, with Flask/template dashboard running on localhost and controlling local managed runtimes  
**Project Type**: Existing Python trading bot with local dashboard/tray application and app-owned runtime lifecycle backend  
**Performance Goals**: A control action should acknowledge within one dashboard roundtrip and reflect the resulting runtime state within the next monitor refresh cycle  
**Constraints**: Preserve live-trading safeguards, remain local single-operator only, avoid introducing a separate frontend framework, support both stock and crypto symbols, and keep the tray non-authoritative for control execution in this phase  
**Scale/Scope**: Small local symbol set, one operator, one local monitor session, and a bounded recent-action history covering mixed stock and crypto runtime operations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: The plan extends the existing Flask monitor, runtime manager, monitor payload model, and local file-backed evidence flow rather than introducing a new control frontend or service.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: The feature only exposes runtime lifecycle controls and must reuse existing live safeguards and mode distinctions; no direct order-entry path is added.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: No new dependencies are planned.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Validation will include unit tests for control state and confirmation flow, contract tests for dashboard payload and action results, smoke tests for POST action routes, and manual local start/stop/restart checks for both stock and crypto symbols.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence will include dashboard control affordances, control result messaging, runtime state transitions, recent control activity entries, runtime registry updates, and continued symbol-scoped trading evidence after a dashboard-issued start or restart.

## Project Structure

### Documentation (this feature)

```text
specs/009-interactive-bot-controls/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- dashboard-control-contract.md
|   `-- monitor-control-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- monitor.py
|   |-- tray.py
|   |-- runtime_manager.py
|   `-- main.py
|-- config/
|   `-- settings.py
`-- strategy/
    `-- signals.py

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

**Structure Decision**: Reuse the current Flask monitor as the interactive control surface and extend the existing runtime-manager module plus runtime registry rather than adding a separate frontend stack, a new control service, or external orchestration.

## Control Evidence Strategy

- **Action availability evidence**: Each symbol instance must expose what lifecycle actions are currently allowed so the operator can tell whether a symbol can be started, stopped, or restarted.
- **Action outcome evidence**: Every dashboard-issued action must return a readable success, failure, or blocked outcome in the same operator flow.
- **Recent control history**: A bounded recent-action list becomes part of the monitor-visible evidence so operators can confirm what happened without relying on terminal output.
- **Mode clarity evidence**: Live and paper control contexts must be visible at the decision point and in recent action history.
- **Asset coverage evidence**: Mixed stock-and-crypto symbol control flows must be visible in one dashboard model so stock support does not regress while crypto remains active.
- **Fallback-operability evidence**: The same runtime should remain operable through current CLI commands if dashboard control validation reveals a regression.

## Phase 0: Research

### Research Questions

1. What is the safest interactive pattern for dashboard-issued runtime lifecycle actions in the existing Flask/template monitor without introducing a new frontend stack?
2. Where should recent control activity and per-symbol action availability live so the monitor can stay truthful even when trading logs are quiet?
3. How should live confirmation be handled so dashboard controls remain safe, clear, and consistent with the existing runtime-manager safeguard model?

### Research Decisions (resolved)

See [research.md](./research.md).

## Phase 1: Design & Contracts

### Design Outputs

- **Data model**: Define control request, control availability, control activity, and any runtime-registry extensions required for interactive controls.
- **Contracts**: Define the dashboard action contract and the monitor payload contract additions for control affordances and recent action history.
- **Quickstart**: Define how to run the monitor, issue safe paper/live control actions, and verify behavior across at least one stock symbol and one crypto symbol.
- **Agent context**: Refresh repo agent context so the interactive-control direction is reflected in the project metadata.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: the design reuses the Flask/template monitor, runtime manager, runtime registry, and current monitor/tray state model.
- Trading safety remains satisfied: interactive actions stay within the current runtime-lifecycle boundary and continue to require live-safe confirmation rather than bypassing safeguards.
- Dependency discipline remains satisfied: the design stays inside the current Python stack and existing local app architecture.
- Validation remains proportional: action routing, control state derivation, live-confirmation handling, and mixed stock/crypto visibility are all covered by unit, contract, smoke, and manual checks.
- Observable operations remain satisfied: runtime state, action outcome, recent control history, and mode context become first-class operator-visible evidence.
