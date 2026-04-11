# AI Trading Bot

Modular Python trading bot built around Lumibot and Alpaca. The current app supports historical backtesting, paper/live runtime guardrails, configurable symbols and risk settings, decision/fill logging, and a Flask-based local monitoring dashboard.

## Status

This project is functional for local development and backtesting, but Alpaca News access currently falls back to neutral sentiment when the API returns authorization errors. Live execution is intentionally fail-closed unless the live safeguards are explicitly enabled.

## Requirements

- Python 3.10
- Alpaca credentials for paper/live trading and market data access
- Windows PowerShell examples below, but the Python package is cross-platform in principle

## Local Setup

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For editable package-style development:

```powershell
python -m pip install -e ".[dev]"
```

If editable install fails in this venv with a setuptools/distutils assertion, use:

```powershell
$env:SETUPTOOLS_USE_DISTUTILS='stdlib'
python -m pip install -e ".[dev]"
```

Optional model and local FinBERT dependencies:

```powershell
python -m pip install -e ".[dev,model,sentiment]"
```

## Configuration

Set runtime configuration through environment variables or local `.env` files. Common variables include:

- `API_KEY`
- `API_SECRET`
- `BASE_URL`
- `SYMBOLS`
- `PAPER_TRADING`
- `LIVE_TRADING_ENABLED`
- `LIVE_RUN_CONFIRMATION`
- `LIVE_CONFIRMATION_TOKEN`
- `BACKTEST_START`
- `BACKTEST_END`

Live trading requires both the persistent live enable flag and the per-run confirmation token. If either is missing, the runtime blocks live execution.

## Commands

Run a quick backtest from the source checkout:

```powershell
python -m tradingbot.app.main --mode backtest --quick-backtest --quick-days 10
```

After editable install, the same runner is available as:

```powershell
tradingbot --mode backtest --quick-backtest --quick-days 10
```

Start the live/paper runtime path:

```powershell
tradingbot --mode live
```

Run the dashboard from the repository checkout:

```powershell
python monitor_app.py
```

Then open:

```text
http://localhost:8080
```

## Validation

```powershell
python -m pytest tests/unit/test_signal_logic.py tests/unit/test_position_sizing.py tests/unit/test_news_fallback.py tests/unit/test_model_fallback.py tests/smoke/test_backtest_entrypoint.py tests/smoke/test_paper_mode_guardrails.py
```

## GitHub Release Flow

1. Confirm tests pass.
2. Commit source changes, but do not commit `.venv`, `__pycache__`, `.pyc`, or generated backtest artifacts.
3. Push the branch to GitHub.
4. Create a GitHub release tag such as `v0.1.0`.
5. In the release notes, include the setup command:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

For package-style installs directly from GitHub:

```powershell
python -m pip install "git+https://github.com/YOURNAME/ai_trading_bot.git@v0.1.0"
```
