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
- `CRYPTO_SYMBOLS`
- `ALPACA_CRYPTO_UNIVERSE`
- `PAPER_TRADING`
- `LIVE_TRADING_ENABLED`
- `LIVE_RUN_CONFIRMATION`
- `LIVE_CONFIRMATION_TOKEN`
- `BACKTEST_START`
- `BACKTEST_END`

Live trading requires both the persistent live enable flag and the per-run confirmation token. If either is missing, the runtime blocks live execution.

Crypto symbols can be configured explicitly with Alpaca slash symbols:

```powershell
$env:SYMBOLS="F"
$env:CRYPTO_SYMBOLS="BTC/USD,ETH/USD,SOL/USD"
```

For a broader Alpaca crypto allow-list, set:

```powershell
$env:ALPACA_CRYPTO_UNIVERSE="usd"
```

Supported values are:

- `none`: do not add a built-in crypto universe
- `usd`: add Alpaca-supported USD-quoted crypto pairs such as `BTC/USD`, `ETH/USD`, `SOL/USD`, `DOGE/USD`, and other active USD pairs
- `all`: add all tracked Alpaca crypto pairs, including `USDC`, `USDT`, and `BTC` quote pairs

For live trading, keep the active list intentionally small. Lumibot live execution should be run one symbol per process, so use explicit `CRYPTO_SYMBOLS` for the pairs you actually want active.

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

Run the monitor like a local app from the package entrypoint:

```powershell
tradingbot-monitor
```

Run the monitor without the tray icon:

```powershell
tradingbot-monitor --no-tray
```

Useful monitor options:

- `--host 127.0.0.1`
- `--port 8080`
- `--refresh-seconds 15`
- `--no-tray`
- `--read-only`

Stopping the monitor:

- Browser-only mode: `Ctrl+C` in the terminal running `tradingbot-monitor --no-tray`
- Tray mode: use `Exit Monitor` from the tray menu, or `Ctrl+C` if launched in the foreground shell

The monitor remains read-only. It does not place, approve, cancel, or modify trades.

Monitor troubleshooting:

- Blank browser page: confirm you launched from the repo root or used `tradingbot-monitor`, then open the exact host and port you passed on the command line.
- Wrong working directory: run `cd C:\Users\Beau\ai_trading_bot` before `python monitor_app.py` or module-style commands so templates and local logs resolve correctly.
- Missing logs: the monitor still starts, but it will show `no_data` or warning states until runtime evidence exists under the expected `logs/paper_validation*` paths.
- Tray unavailable: use `tradingbot-monitor --no-tray` to keep the dashboard usable if `pystray` cannot attach to the local desktop session.

Generated runtime evidence:

- `logs/paper_validation*` contains local operator evidence and should stay out of commits unless you intentionally want to preserve example artifacts.

## Validation

```powershell
python -m pytest tests/unit/test_signal_logic.py tests/unit/test_position_sizing.py tests/unit/test_news_fallback.py tests/unit/test_model_fallback.py tests/smoke/test_backtest_entrypoint.py tests/smoke/test_paper_mode_guardrails.py
```

Monitor validation:

```powershell
python -m pytest tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/unit/test_monitor_data.py tests/unit/test_tray_state.py tests/smoke/test_monitor_entrypoint.py
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
