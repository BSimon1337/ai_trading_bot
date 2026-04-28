# Implementation Plan: Runtime Manager

**Branch**: `008-runtime-manager` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/008-runtime-manager/spec.md`

## Summary

Introduce an application-owned runtime manager so the bot can launch, stop, restart, and track one managed process per symbol without relying on manual PowerShell windows. The implementation will reuse the existing Python app, monitor, tray, config, and symbol-specific CSV evidence patterns; add a small runtime registry and lifecycle layer; surface runtime state in the dashboard and tray; and preserve existing live-trading safeguards instead of creating a backdoor control path.

## Runtime Scope

- **Runtime layer added**: A new `tradingbot/app/runtime_manager.py` module becomes the authoritative owner for local bot process lifecycle.
- **Launch flow reused**: Existing `tradingbot/app/main.py` live-mode entrypoint remains the process target for each managed symbol runtime.
- **Monitor surface reused**: `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, and `templates/monitor.html` remain the operator-facing surfaces and gain runtime-manager state visibility.
- **Config path reused**: Existing `tradingbot/config/settings.py` and current symbol/risk/env patterns remain the source of launch inputs for the initial runtime-manager feature.
- **Evidence path reused**: Existing symbol-scoped decision, fill, and snapshot CSV files remain the runtime evidence source for trading behavior; runtime manager adds process/session state on top.
- **Lifecycle ownership shift**: Manual PowerShell windows become optional recovery/debugging tools rather than the primary way to manage bot runtimes.
- **Runtime state persistence**: One local app-owned runtime-registry file becomes the authoritative process/session state source for monitor and tray refreshes.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Python runtime stack plus standard-library `subprocess`, `threading`, `json`, `pathlib`, and `dataclasses`; no new third-party dependency planned  
**Storage**: Existing CSV runtime evidence plus a local runtime-registry JSON/state file for managed process lifecycle metadata  
**Testing**: pytest unit, contract, and smoke tests covering runtime registry behavior, start/stop/restart flows, monitor payload shaping, and launch-path safety behavior  
**Target Platform**: Local Windows desktop first, with monitor behavior remaining browser-based and runtime logic staying Python-only  
**Project Type**: Existing Python trading bot with local dashboard/tray app growing into an application-owned runtime backend  
**Performance Goals**: Start, stop, or refresh managed symbol state within a few seconds locally; reflect runtime lifecycle changes in the monitor within one refresh cycle  
**Constraints**: Preserve live-trading safety controls; keep one live process per symbol because Lumibot live multi-strategy execution is not supported; avoid requiring manual process inspection as the primary operator workflow; remain local single-machine only  
**Scale/Scope**: Single operator, small symbol set, a handful of concurrent local bot processes, one local monitor, and symbol-scoped runtime evidence under the existing log layout

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: The plan extends the existing Python app and monitor modules, reuses `tradingbot.app.main` as the process target, and adds one focused runtime-manager layer rather than introducing a new stack.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: Runtime control stays inside existing live-safety expectations; no new order-flow path is introduced; live starts and restarts remain explicit and guarded.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: No new third-party dependencies are planned.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Validation will include runtime-manager unit tests, monitor/tray contract updates, local launch smoke checks, and manual verification of start/stop/restart state transitions.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence includes runtime registry state, per-symbol process/session state in the dashboard, last lifecycle event, runtime failure or stop reason, and continued symbol-scoped decision/fill/snapshot evidence after runtime-manager launches.

## Project Structure

### Documentation (this feature)

```text
specs/008-runtime-manager/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- runtime-manager-contract.md
|   `-- monitor-runtime-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- main.py
|   |-- live.py
|   |-- monitor.py
|   |-- tray.py
|   `-- runtime_manager.py
|-- config/
|   `-- settings.py
`-- execution/
    `-- logging.py

templates/
`-- monitor.html

monitor_app.py

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

**Structure Decision**: Add one focused runtime-manager module inside `tradingbot/app/` and extend the existing monitor and tray surfaces rather than creating a separate service, frontend stack, or external supervisor. This keeps the architecture aligned with the current local-app direction while solving the process-ownership gap.

## Runtime Evidence Strategy

- **Managed runtime registry**: A lightweight local registry becomes the source of truth for whether each symbol runtime is starting, running, stopped, restarting, failed, or paused.
- **Lifecycle evidence**: Start, stop, restart, and failure transitions are captured as operator-visible lifecycle events so the monitor can explain the current process state.
- **Trading evidence continuity**: Existing symbol-scoped decision, fill, and snapshot CSVs remain the source of trading behavior and must continue working when launched by the runtime manager.
- **Fresh-session precedence**: New runtime sessions must supersede stale process failures or older sessions for the same symbol in monitor state classification.
- **Operational confirmation points**: Successful runtime-manager behavior will be confirmed through registry entries, monitor runtime-state fields, tray summaries, and continued per-symbol CSV updates after launch.

## Phase 0: Research

### Research Questions

1. What is the safest local standard-library process-management pattern for starting and stopping long-running Python bot processes on Windows while keeping symbol ownership explicit?
2. How should runtime-manager state be persisted locally so the monitor can read current lifecycle information without requiring live in-memory coupling?
3. What is the best way to express live-mode safety for runtime-manager starts and restarts without duplicating or bypassing existing live-trading safeguards?

### Research Decisions (resolved)

See [research.md](./research.md).

## Phase 1: Design & Contracts

### Design Outputs

- **Data model**: Define the managed runtime, runtime session, runtime registry, and lifecycle event records used by the app and monitor.
- **Contracts**: Define the runtime-manager interface contract and the monitor payload contract additions for runtime state.
- **Quickstart**: Define how to launch the monitor with the new runtime-manager-aware flow and how to validate process state transitions safely.
- **Agent context**: Update repo agent context so the new runtime-manager technology decisions are reflected in project guidance.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: the design adds one runtime-manager module inside the current app layer and extends current monitor/tray flows.
- Trading safety remains satisfied: runtime-manager actions reuse current live-safety assumptions and do not create a hidden execution path.
- Dependency discipline remains satisfied: the design stays inside the current Python stack and standard library.
- Validation remains proportional: runtime-manager lifecycle logic, monitor state integration, and local launch behavior are all covered by unit, contract, smoke, and manual checks.
- Observable operations remain satisfied: runtime lifecycle becomes first-class operator evidence alongside the existing decision, fill, and snapshot logs.
