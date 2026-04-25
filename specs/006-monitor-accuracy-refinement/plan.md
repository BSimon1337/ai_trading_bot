# Implementation Plan: Monitor Accuracy Refinement

**Branch**: `006-monitor-accuracy-refinement` | **Date**: 2026-04-25 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/006-monitor-accuracy-refinement/spec.md`

## Summary

Refine the existing local monitor so operators can trust the current view during live trading. The implementation will keep the current Flask/template and tray architecture, tighten status aging so healthy restarts override stale failures, derive one authoritative account summary per refresh, improve per-asset held-value fallback behavior, separate issues from informational notes, add clearer per-bot activity/rejection telemetry, and define safe handling of old runtime evidence so historical noise does not pollute active monitoring.

## Reused Monitor Surface

- **Monitor modules reused**: `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, and `monitor_app.py` remain the runtime entrypoints and payload assembly layer for this refinement.
- **UI surface reused**: `templates/monitor.html` remains the operator-facing dashboard and will absorb the issue/note split, timestamp clarity, and current-versus-historical evidence cues.
- **Payload contracts reused**: Existing `/`, `/health`, and `/api/status` monitor routes remain the contract boundary. This feature refines payload semantics rather than creating new routes.
- **Evidence sources reused**: Existing decision, fill, and snapshot CSV evidence stays authoritative, with refinement focused on freshness precedence, fallback valuation, and safe historical filtering.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Flask, pandas, python-dotenv, pytest, pystray, Pillow stack already used by the monitor feature  
**Storage**: Existing local CSV runtime evidence files under configured log paths; no database  
**Testing**: pytest unit, contract, and smoke tests focused on monitor data shaping, state aging, held-value fallback logic, issue/note classification, and log-retention behavior  
**Target Platform**: Local Windows desktop first, with browser dashboard remaining usable cross-platform  
**Project Type**: Existing Python trading bot with local web dashboard and tray monitor  
**Performance Goals**: Preserve current local monitor responsiveness, with dashboard status refreshes remaining operator-usable for multiple monitored instances within a few seconds from local evidence  
**Constraints**: Read-only monitoring only; no credential display; no changes to order placement or live safeguards; historical evidence must remain available for debugging while active monitoring stays clean  
**Scale/Scope**: Single local operator monitoring a small set of stock and crypto bot processes sharing one account and multiple symbol-specific evidence files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: The plan stays within `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, `templates/monitor.html`, existing CSV evidence, and current pytest patterns.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: This feature is read-only and changes only monitor interpretation, presentation, and evidence hygiene. No trading APIs or live-control flows are added.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: No new dependencies are planned.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Validation will include fixture-driven monitor tests, contract updates, smoke verification for monitor startup, and manual dashboard checks against mixed current/historical evidence.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence includes account overview values, per-symbol held value, last decision/fill timestamps, broker rejection counters, issue-versus-note grouping, stale-failure recovery behavior, and clean dashboard state after log rotation or archival.

## Project Structure

### Documentation (this feature)

```text
specs/006-monitor-accuracy-refinement/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- dashboard-monitor-contract.md
|   `-- tray-monitor-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- monitor.py
|   |-- tray.py
|   `-- main.py
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
|   `-- test_monitor_entrypoint.py
`-- unit/
    |-- test_monitor_data.py
    `-- test_tray_state.py
```

**Structure Decision**: Keep the refinement inside the existing monitor/tray modules and template rather than introducing a new runtime boundary. Validation stays in the existing contract, smoke, and unit test files because this feature is an interpretation and operator-clarity refinement, not a new subsystem.

## Evidence Sources

- **Decision evidence**: Symbol and system decision CSV rows remain the source for current action, latest reason, decision timing, blocked/failure history, and operator-facing notes.
- **Fill evidence**: Fill CSV rows remain the source for last fill time, rejection counting, and one trusted valuation input when recent fills are available.
- **Snapshot evidence**: Snapshot CSV rows remain the preferred source for account-level cash, equity, day PnL, and current position quantity when fresh enough to trust.
- **Historical evidence handling**: Archived, stale, or malformed evidence remains available for manual review, but must be bounded so it does not dominate active status classification after a healthy restart.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: design artifacts extend the current dashboard, tray, CSV evidence parsing, and test structure.
- Trading safety remains satisfied: the monitor stays read-only and does not alter order flow, approvals, or live safeguards.
- Dependency discipline remains satisfied: no new packages are introduced.
- Validation remains proportional: fixture-driven state-aging, held-value, and retention scenarios plus contract and smoke checks cover the operator risk of incorrect status display.
- Observable operations remain satisfied: the refined dashboard will expose clearer account summary values, activity timestamps, rejection counts, note/issue grouping, and current-versus-historical evidence behavior.
