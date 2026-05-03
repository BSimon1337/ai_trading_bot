# AI Trading Bot: Professor Run Guide

This project is a Python 3.10 machine-learning trading bot with backtesting, paper/live runtime guardrails, local evidence logs, and a Flask monitoring dashboard.

## Quick Start

From a fresh checkout:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Optional editable install:

```powershell
python -m pip install -e ".[dev]"
```

If editable install fails because of a setuptools/distutils issue:

```powershell
$env:SETUPTOOLS_USE_DISTUTILS='stdlib'
python -m pip install -e ".[dev]"
```

## Run a Quick Backtest

This quick backtest is the recommended grading/demo command. It does not require Alpaca paper/live trading credentials. It uses the project's local/offline-safe paths where available; if external news or sentiment dependencies are unavailable, the bot falls back to neutral sentiment.

```powershell
python -m tradingbot.app.main --mode backtest --quick-backtest --quick-days 10
```

If the editable install was used, this equivalent command should also work:

```powershell
tradingbot --mode backtest --quick-backtest --quick-days 10
```

Alpaca credentials are only needed for fresh data collection or paper/live broker integration.

## Run the Monitoring Dashboard

From the repository root:

```powershell
python monitor_app.py
```

Then open:

```text
http://localhost:8080
```

Alternative package entrypoint:

```powershell
tradingbot-monitor --no-tray --host 127.0.0.1 --port 8080
```

Then open:

```text
http://127.0.0.1:8080
```

## Run Tests

Core validation:

```powershell
python -m pytest tests/unit/test_signal_logic.py tests/unit/test_position_sizing.py tests/unit/test_news_fallback.py tests/unit/test_model_fallback.py tests/smoke/test_backtest_entrypoint.py tests/smoke/test_paper_mode_guardrails.py
```

Dashboard validation:

```powershell
python -m pytest tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/unit/test_monitor_data.py tests/unit/test_tray_state.py tests/smoke/test_monitor_entrypoint.py
```

## Optional Environment Configuration

The project can read settings from environment variables or local `.env` files. Common variables include:

```text
API_KEY
API_SECRET
BASE_URL
SYMBOLS
CRYPTO_SYMBOLS
PAPER_TRADING
LIVE_TRADING_ENABLED
LIVE_RUN_CONFIRMATION
LIVE_CONFIRMATION_TOKEN
BACKTEST_START
BACKTEST_END
```

For a safe local demo, paper mode should remain enabled. Live trading is intentionally blocked unless multiple live-trading safeguards are explicitly configured.

## Important Safety Notes

- Do not commit or share real Alpaca API keys.
- Live trading is disabled by default and should not be enabled for grading.
- Generated runtime logs are local evidence artifacts and may vary by machine.
- The submitted paper and presentation are in:

```text
manuscript/
presentation/
```
