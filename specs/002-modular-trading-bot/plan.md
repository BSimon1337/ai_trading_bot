# Implementation Plan: Modular Multi-Asset Trading Bot

**Branch**: `002-modular-trading-bot` | **Date**: 2026-04-08 | **Spec**: [spec.md](c:/Users/Beau/ai_trading_bot/specs/002-modular-trading-bot/spec.md)
**Input**: Feature specification from `/specs/002-modular-trading-bot/spec.md`

## Summary

Refactor the existing trading bot into explicit Python 3.10 modules for config, data/news,
sentiment, strategy, risk, execution, and app entrypoints while preserving the current
Lumibot plus Alpaca workflow. The design keeps paper trading and backtesting as first-class
paths, adds a stricter two-step live-trading gate using environment variables, and improves
testability with `pytest` coverage for signal logic and position sizing.

## Technical Context

**Language/Version**: Python 3.10  
**Primary Dependencies**: Lumibot, Alpaca integration via Lumibot broker support, pandas, joblib, python-dotenv, pytest  
**Storage**: File-based CSV logs, model artifacts in `models/`, environment variables from `.env` / `env/.env`  
**Testing**: `pytest` for unit-focused signal and sizing tests, plus targeted backtest/paper smoke checks  
**Target Platform**: Local Windows development, paper/live trading runtime, and backtest execution on a Python host  
**Project Type**: Single Python application with CLI/app entrypoints and operator dashboard  
**Performance Goals**: Daily trading decision cycle for configured symbols completes within 60 seconds for standard operator runs; startup preflight completes within 30 seconds; backtest smoke run completes within 5 minutes on a typical dev machine  
**Constraints**: Keep Lumibot and Alpaca integration; use environment variables for all credentials and mode switches; fail closed for live trading; preserve operator-visible decision logging; prefer existing project patterns unless modular separation clearly improves maintainability  
**Scale/Scope**: Single-repo bot handling configurable stock and crypto symbol sets, daily or periodic decision evaluation, backtesting, paper trading, and guarded live trading

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Existing-project consistency: PASS. The plan keeps the current Python-first runtime and root-level workflows while introducing a contained module package rather than a new service boundary.
- Trading safety: PASS. Live execution remains blocked by default and adds a two-step environment-variable gate plus preflight validation.
- Reproducible dependencies: PASS. No npm packages are introduced. Python dependencies remain aligned with the current stack; `pytest` is the only required testing dependency if not already present.
- Risk-proportionate validation: PASS. The plan includes unit tests for signal logic and sizing plus smoke validation for backtest and paper mode.
- Observable operations: PASS. Decision, fill, and run-mode evidence remain explicit through CSV logs and runtime logging, with monitoring compatibility preserved.

## Project Structure

### Documentation (this feature)

```text
specs/002-modular-trading-bot/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
tradingbot/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── data/
│   ├── __init__.py
│   └── news.py
├── sentiment/
│   ├── __init__.py
│   └── scoring.py
├── strategy/
│   ├── __init__.py
│   ├── signals.py
│   └── lumibot_strategy.py
├── risk/
│   ├── __init__.py
│   └── sizing.py
├── execution/
│   ├── __init__.py
│   ├── broker.py
│   ├── safeguards.py
│   └── logging.py
└── app/
    ├── __init__.py
    ├── backtest.py
    ├── live.py
    └── main.py

tests/
├── unit/
│   ├── test_signal_logic.py
│   └── test_position_sizing.py
└── smoke/
    ├── test_backtest_entrypoint.py
    └── test_paper_mode_guardrails.py

monitor_app.py
templates/
models/
logs/
```

**Structure Decision**: Introduce a single internal `tradingbot/` package with functional
submodules that map directly to the requested responsibilities. Keep existing root-level
artifacts such as `monitor_app.py`, `templates/`, `models/`, and `logs/`, and migrate the
current top-level logic into the new package in place rather than creating a separate service.

## Migration Baseline

- Existing retained entrypoints at repo root: `tradingbot.py`, `backtester.py`, and `monitor_app.py`
- Existing retained domain sources to migrate incrementally: `config.py`, `data_handler.py`,
  `finbert_utils.py`, `strategy.py`, and `portfolio.py`
- Existing retained operator artifacts: `models/`, `logs/`, `templates/`, and `env/.env`
- Phase 1 scaffolding creates the target `tradingbot/` package and `tests/` layout first so later
  implementation can move behavior module by module without breaking the current repo shape

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Internal package extraction | Current logic is spread across top-level files and is hard to test in isolation | Leaving everything in root modules would not satisfy the requested modular split or improve testability |
