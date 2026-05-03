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

The dashboard now controls runtime lifecycle only. It can start, stop, and restart managed bot processes, but it still does not place manual trades, approve broker orders, cancel live orders directly, or edit positions outside the runtime flow.

What the refined monitor now shows:

- one authoritative account overview per refresh
- per-symbol held quantity and symbol-local held-value estimate
- separate `Issues` and `Notes` sections
- last decision time, last fill time, and broker rejection count per bot
- bounded `Historical Context` so archived or older failed evidence stays visible without overriding current state
- current per-symbol sentiment label, confidence, source, and fallback state
- bounded recent headline previews and short sentiment trend history per symbol
- stale and no-headline sentiment explanations without changing the monitor's read-only behavior
- app-owned runtime state per symbol, including session id, lifecycle event, and fresh-session context
- a clear distinction between `running`, `stopped`, `paused`, `failed`, and merely `stale` evidence
- dashboard lifecycle controls for `start`, `stop`, and `restart`
- visible live-vs-paper control context with trusted local live control sessions
- recent control activity across both stock and crypto symbols
- recent runtime events, warning summaries, and order-lifecycle state per symbol
- explicit `Portfolio Freshness` semantics so `current`, `provisional`, `unavailable`, `stale`, and `historical` states are visible instead of implied
- isolated symbol cards so one symbol's held value or account state does not overwrite another card after startup or fills

Recommended monitor startup for your current multi-crypto setup:

```powershell
cd C:\{your_file_path}
.\.venv\Scripts\Activate.ps1
$Host.UI.RawUI.WindowTitle = "AI Trading Bot - Monitor"

$env:SYMBOLS="BTC/USD,ETH/USD,SOL/USD,DOGE/USD"
$env:CRYPTO_SYMBOLS=""
$env:ALPACA_CRYPTO_UNIVERSE="none"

tradingbot-monitor --no-tray --host 127.0.0.1 --port 8080
```

Then open:

```text
http://127.0.0.1:8080
```

Monitor and control troubleshooting:

- Blank browser page: confirm you launched from the repo root or used `tradingbot-monitor`, then open the exact host and port you passed on the command line.
- Wrong working directory: run `cd C:\Users\Beau\ai_trading_bot` before `python monitor_app.py` or module-style commands so templates and local logs resolve correctly.
- Missing logs: the monitor still starts, but it will show `no_data` or warning states until runtime evidence exists under the expected mode-aware paths, such as `logs/live_validation*` for live runs and `logs/paper_validation*` for paper runs.
- Tray unavailable: use `tradingbot-monitor --no-tray` to keep the dashboard usable if `pystray` cannot attach to the local desktop session.
- Historical noise still showing up as current: move older evidence into folders named like `archived`, `history`, or `old`, or set `MONITOR_ARCHIVE_MARKERS` to match your retention folder names.
- Current evidence feeling too old or too aggressive: tune `MONITOR_STALE_AFTER_MINUTES` and `MONITOR_HISTORICAL_ISSUE_LIMIT` for your local workflow.
- Runtime shows `stopped` while old decisions still exist: this is expected once the runtime manager owns lifecycle state; `stopped` now beats stale CSV evidence.
- Live runtime startup is still guarded by `LIVE_RUN_CONFIRMATION`, but the dashboard should satisfy that through its trusted local session instead of a per-click confirmation box.
- Dashboard control appears to do nothing: check the `Recent Control Activity` table first; blocked and failed actions now show there with a reason before you need to inspect terminal output.
- A symbol card shows `Account Cash` instead of a symbol-only cash balance because account cash is shared account-level evidence, while `Held Value` remains symbol-scoped.

## Runtime Manager

The runtime manager is now the intended way to own bot process lifecycle locally. It keeps one managed process per symbol, writes a local runtime registry, and feeds runtime state into the dashboard and tray.

Common lifecycle commands from the repo checkout:

```powershell
python -m tradingbot.app.main --mode runtime-start --managed-symbol BTC/USD
python -m tradingbot.app.main --mode runtime-stop --managed-symbol BTC/USD
python -m tradingbot.app.main --mode runtime-restart --managed-symbol BTC/USD
```

If you omit `--managed-symbol`, the runtime-manager command uses the configured symbol set from env/config.

What the runtime manager preserves:

- one authoritative current runtime entry per symbol
- symbol-scoped decision/fill/snapshot logs
- live-trading guardrails before managed starts and restarts
- recent runtime session history for monitor/tray visibility

What it does not do yet:

- bulk process supervision beyond the local runtime registry
- a separate approval path for live trading beyond the confirmation-token safeguard
- dashboard editing for broader strategy/risk settings

The next planned app layer after this is richer operator management on top of the current runtime controls, including settings and broader application workflow improvements, while continuing to support both stock and crypto symbols through one shared operator experience.

The next monitor-focused refinement after interactive controls is runtime observability hardening. That work is intended to make the dashboard more trustworthy during startup and mixed-symbol activity by:

- reconciling runtime truth against actual managed process state on every refresh
- surfacing recent runtime milestones, warnings, and order-lifecycle progress directly in the dashboard
- labeling provisional-versus-confirmed portfolio state explicitly
- preventing one symbol's held value, cash state, or other portfolio evidence from leaking into another symbol's card after runtimes start

Generated runtime evidence:

- `logs/live_validation*` and `logs/paper_validation*` contain local operator evidence and should stay out of commits unless you intentionally want to preserve example artifacts.

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
Quick monitor launcher:

```powershell
.\start_monitor.ps1
```

Double-click launcher:

```text
start_monitor.cmd
```

Optional examples:

```powershell
.\start_monitor.ps1 -Mode paper
.\start_monitor.ps1 -Mode live -Symbols "SPY,BTC/USD,ETH/USD"
.\start_monitor.ps1 -Tray
```
