# Quickstart: Modular Multi-Asset Trading Bot

## Prerequisites

- Python 3.10 available on the machine
- Project dependencies installed for the trading bot runtime
- `pytest` available in the project environment for unit and smoke validation
- Environment variables configured for credentials, symbols, risk settings, and mode switches

## Environment Setup

Set credentials and runtime switches through environment variables or the existing `.env` files.

Required categories:
- Alpaca credentials
- Paper/live mode selection
- Live-trading persistent enable flag
- Live-trading per-run confirmation value
- Symbol list
- Risk settings
- Log output paths

## Repository Baseline

- Current root-level runtime files remain in place during migration: `tradingbot.py`,
  `backtester.py`, `config.py`, `data_handler.py`, `finbert_utils.py`, `strategy.py`,
  and `portfolio.py`
- Phase 1 creates the target package layout under `tradingbot/` and the test layout under `tests/`
- Later phases migrate behavior into the package while preserving the existing operator workflow

## Recommended Validation Flow

1. Confirm Python 3.10 is active for the project environment.
2. Set paper mode and provide Alpaca paper credentials.
3. Run the backtest entrypoint against a short historical window.
4. Run the paper-trading entrypoint and confirm:
   - decisions are logged
   - fills or blocked actions are logged
   - run mode is clearly visible in outputs
5. Attempt a live run without one live safeguard enabled and confirm startup fails closed.
6. Enable both live safeguards only when intentionally validating live readiness.

## Test Commands

```powershell
pytest tests/unit/test_signal_logic.py
pytest tests/unit/test_position_sizing.py
pytest tests/smoke/test_backtest_entrypoint.py
pytest tests/smoke/test_paper_mode_guardrails.py
```

## Operational Checks

- Verify decision logs include no-trade and blocked-trade outcomes
- Verify fill logs remain empty for blocked live runs
- Verify paper runs still produce operator-visible activity
- Verify daily trading runs complete within the planned performance budget
