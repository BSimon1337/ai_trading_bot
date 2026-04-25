# Implementation Plan: Preflight Validation and Offline Development Mode

**Branch**: `004-preflight-offline-mode` | **Date**: 2026-04-11 | **Spec**: [spec.md](c:/Users/Beau/ai_trading_bot/specs/003-preflight-offline-mode/spec.md)
**Input**: Feature specification from `/specs/003-preflight-offline-mode/spec.md`

## Summary

Add an operator-facing preflight validation flow and an offline development mode for backtests. The design extends the existing Python 3.10 modular package, reusing config, data/news, sentiment, strategy, risk, execution, logging, and app entrypoint patterns. The preflight command reports credential, market data/news, model, dependency, log path, symbol, and paper/live safeguard readiness before runtime. Offline development mode lets backtests consume local/cached news fixtures and explicitly records whether decisions used external, local, or neutral fallback sentiment.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Existing pinned runtime stack in `requirements.txt` / `pyproject.toml`: Lumibot, Alpaca integration via Lumibot and `alpaca-py`, pandas, numpy, scipy, yfinance, joblib, python-dotenv, Flask, pytest  
**Storage**: File-based CSV logs, local fixture files for cached/offline news, model artifacts in `models/`, environment variables from `.env` / `env/.env`  
**Testing**: `pytest` unit tests for readiness checks, fixture loading, log-path checks, model diagnostics, Alpaca News failure handling, and live safeguard blocking; smoke tests for CLI routing  
**Target Platform**: Local Windows development and Python host environments used for backtests, paper trading, and guarded live trading  
**Project Type**: Single Python application/package with CLI app entrypoints and a Flask operator dashboard  
**Performance Goals**: Preflight summary completes in <= 30 seconds for normal local checks; offline fixture loading for a smoke backtest adds <= 5 seconds; existing smoke backtest target remains <= 5 minutes on a typical dev machine  
**Constraints**: Preserve fail-closed live trading; do not require Alpaca News for offline-capable backtests; do not bypass existing paper/live guardrails; keep new behavior observable in logs/CSV evidence; avoid new dependencies unless strictly necessary  
**Scale/Scope**: Single-repo bot with configurable stock and crypto symbols, local/backtest development, paper trading, guarded live trading, and operator-readable diagnostics

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Existing-project consistency: PASS. The plan extends the existing `tradingbot/` package and app entrypoint rather than adding a new runtime boundary.
- Trading safety: PASS. Live execution remains fail-closed and offline development mode is scoped to backtests/local validation.
- Reproducible dependencies: PASS. No new dependencies are planned. Existing dependencies remain pinned in `requirements.txt` and `pyproject.toml`; no npm packages are introduced.
- Risk-proportionate validation: PASS. The plan includes unit coverage for readiness, fixture, model, and live-guardrail behavior plus smoke validation for CLI routing.
- Observable operations: PASS. Preflight output, decision records, and fallback-source evidence will expose pass/warning/fail status and sentiment data source.

## Project Structure

### Documentation (this feature)

```text
specs/003-preflight-offline-mode/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- preflight-cli-contract.md
`-- checklists/
    `-- requirements.md
```

### Source Code (repository root)

```text
tradingbot/
|-- config/
|   `-- settings.py
|-- data/
|   `-- news.py
|-- execution/
|   |-- logging.py
|   `-- safeguards.py
|-- strategy/
|   `-- lumibot_strategy.py
`-- app/
    |-- main.py
    `-- preflight.py        # planned

tests/
|-- unit/
|   |-- test_preflight_readiness.py       # planned
|   |-- test_offline_news_fixtures.py     # planned
|   |-- test_log_path_readiness.py        # planned
|   `-- test_model_fallback.py
`-- smoke/
    `-- test_preflight_entrypoint.py      # planned

data/
`-- offline_news/                         # planned local fixtures
```

**Structure Decision**: Keep the feature inside the existing modular package. Add a focused `tradingbot.app.preflight` entrypoint for readiness reporting and extend `tradingbot.data.news` to support local fixture sources during backtests. Preserve existing root-level compatibility shims and the current dashboard layout.

## Complexity Tracking

No constitution violations or justified complexity exceptions are required.

## Post-Design Constitution Check

- Existing-project consistency: PASS. Phase 1 design keeps all interfaces in the current package/CLI/logging patterns.
- Trading safety: PASS. Contracts explicitly keep offline mode backtest-only and preserve live guardrail failure semantics.
- Reproducible dependencies: PASS. No new dependencies are required by design artifacts.
- Risk-proportionate validation: PASS. Quickstart and contracts define test coverage for each high-risk readiness path.
- Observable operations: PASS. Data model and contracts include readiness report details and sentiment data-source evidence.
