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
   - Preferred modular path: `python -m tradingbot.app.main --mode backtest --quick-backtest --quick-days 10`
   - Compatibility path: `python tradingbot.py --mode backtest --quick-backtest --quick-days 10`
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
- Verify backtest runs write a `mode=backtest` completion decision record
- Verify fill logs remain empty for blocked live runs
- Verify paper runs still produce operator-visible activity
- Verify daily trading runs complete within the planned performance budget

## Validation Notes

- 2026-04-11: `python -m pytest tests/unit/test_signal_logic.py tests/unit/test_position_sizing.py tests/smoke/test_backtest_entrypoint.py tests/smoke/test_paper_mode_guardrails.py` passed with 15 tests and 1 warning on Python 3.13.1 after installing `pytest==8.3.5` in the active user environment.
- 2026-04-11: mocked paper startup routing completed in 0.0113 seconds, within the 30-second startup preflight target.
- 2026-04-11: dashboard data contract check passed for `latest_mode=paper`, `latest_asset_class=stock`, and `status=paper`; local Flask import was stubbed because Flask is not installed in the active interpreter.
- 2026-04-11: full daily trading runtime against live market dependencies was not measured in this environment; use a paper run with configured symbols to validate the 60-second daily decision-cycle target before live deployment.
