# Implementation Plan: Sentiment Observability

**Branch**: `007-sentiment-observability` | **Date**: 2026-04-26 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/007-sentiment-observability/spec.md`

## Summary

Extend the existing local monitor so each bot exposes explainable sentiment context, not just trade and health state. The implementation will reuse the current FinBERT scoring path, Alpaca/offline-news ingestion, strategy decision logging, and Flask/template monitor surface to show latest sentiment label, confidence, source, fallback state, headline evidence, and short sentiment history in a bounded operator-friendly format.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing Flask, pandas, python-dotenv, Lumibot runtime stack, local FinBERT path through `transformers` and `torch`, pytest  
**Storage**: Existing local CSV runtime evidence files plus current news/sentiment runtime flows; no database  
**Testing**: pytest unit, contract, and smoke validation for sentiment payload shaping, fallback-state handling, headline preview behavior, and dashboard rendering  
**Target Platform**: Local Windows desktop first, with browser dashboard remaining usable cross-platform  
**Project Type**: Existing Python trading bot with local web dashboard and tray monitor  
**Performance Goals**: Preserve current monitor responsiveness while adding bounded sentiment context per monitored symbol within the normal refresh cadence  
**Constraints**: Read-only monitor only; no trade-control behavior; no new dependency expected; sentiment context must be bounded and must clearly distinguish real FinBERT output from neutral fallback behavior  
**Scale/Scope**: Single local operator monitoring a small set of stock and crypto bot processes, usually one symbol per live process

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Reuse or extend existing project patterns, modules, and workflows. Document any deviation and why following the current pattern was insufficient.  
  **PASS**: The feature extends `tradingbot/sentiment/scoring.py`, `tradingbot/data/news.py`, `tradingbot/strategy/lumibot_strategy.py`, `tradingbot/app/monitor.py`, `templates/monitor.html`, and existing monitor tests.
- Preserve or improve trading safety controls for order flow, risk limits, config handling, and live-trading guardrails.  
  **PASS**: The feature is observability-only and does not alter order placement, approvals, or live guardrails.
- List every new dependency. For npm packages, record the exact pinned version and confirm the selected release is at least 7 days old.  
  **PASS**: No new dependencies are planned.
- Define validation proportional to the operational risk of the change, including any backtests, smoke tests, manual checks, or log/dashboard verification.  
  **PASS**: Validation will include sentiment-specific unit tests, dashboard contract coverage, monitor smoke checks, and manual dashboard verification against fallback and headline scenarios.
- Identify the logs, CSVs, dashboard signals, or other operator-visible evidence that will confirm the feature works in practice.  
  **PASS**: Evidence includes decision-log sentiment fields, new sentiment payload fields in `/api/status`, dashboard sentiment cards/details, fallback-state badges, headline preview rows, and trend/history summaries.

## Project Structure

### Documentation (this feature)

```text
specs/007-sentiment-observability/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- dashboard-monitor-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
tradingbot/
|-- app/
|   |-- monitor.py
|   `-- tray.py
|-- data/
|   `-- news.py
|-- sentiment/
|   `-- scoring.py
`-- strategy/
    `-- lumibot_strategy.py

templates/
`-- monitor.html

tests/
|-- contract/
|   `-- test_dashboard_monitor_contract.py
|-- smoke/
|   `-- test_monitor_entrypoint.py
`-- unit/
    `-- test_monitor_data.py
```

**Structure Decision**: Keep the feature inside the existing strategy-to-monitor evidence path. Sentiment context will be added to the existing dashboard payload and template rather than introducing a new runtime surface or UI stack.

## Sentiment Evidence Sources

- **Strategy decision evidence**: Existing decision rows already carry `sentiment_source`, `sentiment_probability`, and `sentiment_label`, and will remain the main current-state feed for dashboard sentiment snapshots.
- **News ingestion evidence**: `DataHandler` already knows whether recent news came from Alpaca, local fixtures, or neutral fallback, and can be extended to surface bounded headline records and count metadata.
- **FinBERT runtime state**: The scoring layer already distinguishes successful model use from dependency-load failure or neutral fallback and should expose that state in an operator-readable form.
- **Dashboard evidence**: `/api/status` and `templates/monitor.html` remain the operator-facing contract boundary for sentiment visibility.

## Reused Runtime Path

- **Source modules reused**: `tradingbot/data/news.py` remains the fetch-and-normalize layer for Alpaca and offline news records, and `tradingbot/sentiment/scoring.py` remains the FinBERT and fallback interpretation layer.
- **Runtime producer reused**: `tradingbot/strategy/lumibot_strategy.py` remains the place where live and paper strategy iterations convert news into sentiment fields and write operator-visible decision evidence.
- **Monitor consumer reused**: `tradingbot/app/monitor.py` and `templates/monitor.html` remain the read-only monitor surface that will consume and present the sentiment snapshot, headline preview, and short trend context.
- **Safety boundary reused**: `tradingbot/app/tray.py` remains a read-only summary surface only; no trade controls or strategy-changing actions are part of this feature.

## Complexity Tracking

No constitution violations are planned.

## Post-Design Constitution Check

- Existing-project consistency remains satisfied: the design stays inside current strategy, data, monitor, and template modules.
- Trading safety remains satisfied: the feature is read-only and does not modify decision thresholds or broker execution paths.
- Dependency discipline remains satisfied: no new package is required to expose already-available sentiment behavior.
- Validation remains proportional: unit, contract, and smoke checks will cover fallback state, headline evidence, and dashboard rendering.
- Observable operations remain satisfied: the feature explicitly improves operator-visible sentiment evidence in logs and monitor output.
