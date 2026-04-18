# Implementation Plan: Dashboard and Tray App

**Branch**: `005-dashboard-tray-app` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/004-dashboard-tray-app/spec.md`

## Summary

Add an operator-facing local monitor that reuses the existing Flask/template dashboard and CSV runtime evidence, then add a system tray launcher/presence so the bot feels like a normal local application while it is being monitored. The implementation will keep the dashboard browser-viewable, add a tray menu for opening the dashboard and exiting the monitor, improve multi-symbol status parsing, and preserve read-only/fail-closed trading behavior.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Flask/pandas/python-dotenv stack; add `pystray==0.19.5` and `Pillow==11.3.0` for tray icon support  
**Storage**: Existing local CSV runtime evidence files under configured log paths; no database  
**Testing**: pytest unit, smoke, and contract-style tests for monitor data shaping, dashboard routes, tray state/menu behavior, and malformed log handling  
**Target Platform**: Local Windows desktop first, with browser dashboard usable cross-platform and tray support graceful when unavailable  
**Project Type**: Existing Python trading bot with local web dashboard and desktop tray monitor launcher  
**Performance Goals**: Dashboard renders 10 monitored symbols/instances within 3 seconds from local evidence; tray appears within 10 seconds on supported desktops; refresh interval defaults to 15 seconds or less  
**Constraints**: Read-only monitoring by default; no credential display; no trade approval/order placement from dashboard; live safeguards remain untouched; new dependencies must be exactly pinned and older than 7 days  
**Scale/Scope**: Single local operator monitoring local bot processes and log evidence for stocks and crypto symbols; not a hosted multi-user monitoring service

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: Plan extends `monitor_app.py`, `templates/monitor.html`, existing config/logging modules, and current pytest patterns.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: Monitor is read-only by default and must not place, approve, cancel, or bypass live safeguards.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: New Python dependencies are `pystray==0.19.5` and `Pillow==11.3.0`. No npm packages are planned. PyPI data shows `pystray==0.19.5` uploaded 2023-09-17 and Pillow `11.3.0` released 2025-07-01, both older than 7 days as of 2026-04-18.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Plan includes fixture-driven dashboard status tests, route smoke tests, tray behavior tests with mocks, and manual local launch checks.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence includes monitor dashboard status cards, recent decision/fill tables, stale/blocked/error status labels, tray menu/status text, and monitor startup logs.

## Project Structure

### Documentation (this feature)

```text
specs/004-dashboard-tray-app/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- dashboard-monitor-contract.md
|   `-- tray-monitor-contract.md
|-- checklists/
|   `-- requirements.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- main.py                 # extend CLI modes only if needed
|   |-- monitor.py              # dashboard data assembly and monitor app factory
|   `-- tray.py                 # tray lifecycle/menu/status wrapper
|-- config/
|   `-- settings.py             # monitor env vars if needed
`-- execution/
    `-- logging.py              # reuse log contracts

templates/
`-- monitor.html                # improve dashboard UI/status sections

monitor_app.py                  # compatibility entrypoint for web dashboard

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

**Structure Decision**: Keep the feature in the existing Python package and Flask/template dashboard path. Add small monitor/tray modules under `tradingbot/app/` so root-level entrypoints remain compatibility shims, matching the modularization approach already used for backtest/live/preflight flows.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: design artifacts reuse the current dashboard, template, config, logging, and pytest patterns.
- Trading safety remains satisfied: contracts explicitly keep dashboard/tray behavior read-only and do not introduce order placement or live-safeguard bypasses.
- Dependency discipline remains satisfied: planned dependencies are pinned exactly, documented in research, and older than 7 days. No npm packages are planned.
- Validation remains proportional: contracts, quickstart, fixture-state tests, and manual launch checks cover the operational monitor risk.
- Observable operations remain satisfied: dashboard cards, structured status, tray state, recent issues, and existing CSV evidence provide operator-visible confirmation.
