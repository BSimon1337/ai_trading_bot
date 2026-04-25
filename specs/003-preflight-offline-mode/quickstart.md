# Quickstart: Preflight Validation and Offline Development Mode

## Prerequisites

- Python 3.10 virtual environment active
- Project installed from `requirements.txt` or editable package metadata
- Credentials and mode switches configured through environment variables or existing `.env` files
- Optional local news fixtures prepared for offline backtest development

## Install

```powershell
python -m pip install -r requirements.txt
```

For editable package CLI development:

```powershell
$env:SETUPTOOLS_USE_DISTUTILS='stdlib'
python -m pip install -e ".[dev]"
```

## Preflight Flow

1. Run readiness validation before trading or backtesting:

```powershell
tradingbot --mode preflight
```

If the editable package CLI is not installed yet, run the same entrypoint with:

```powershell
python -m tradingbot.app.main --mode preflight
```

2. Confirm the report separates:
   - credential readiness
   - trading access
   - market data/news access
   - symbol configuration
   - log path writability
   - model availability
   - required and optional dependency availability
   - live safeguard readiness

3. Treat `fail` results as blockers. Treat `warning` results as allowed only when the requested run mode supports a safe fallback.

Dependency diagnostics use different severities:

- Missing required runtime packages such as Lumibot, Alpaca, pandas, joblib, or python-dotenv produce a `fail`.
- Missing optional local FinBERT packages such as transformers or torch produce a `warning`.
- Missing or unloadable saved model files produce a `warning` when `USE_MODEL_SIGNAL=true`; the strategy can fall back to sentiment rules.
- `USE_MODEL_SIGNAL=false` skips saved-model loading and reports a pass for model loadability.

Example pass output:

```text
Preflight readiness: pass
- pass: credentials - Alpaca credential values are present.
- pass: live_safeguards - Live safeguards not required for paper readiness.
```

Example warning output:

```text
Preflight readiness: warning
- warning: alpaca_news_access - News access probe did not complete for SPY: unauthorized
```

Example fail output:

```text
Preflight readiness: fail
- fail: live_safeguards - Live trading is blocked. Set LIVE_TRADING_ENABLED=1 only after paper validation.
```

## Environment Switches

Preflight and offline mode use the existing `.env` / `env/.env` loading pattern.

Core switches:

- `API_KEY` or `ALPACA_API_KEY`: Alpaca key used for readiness probes
- `API_SECRET` or `ALPACA_API_SECRET`: Alpaca secret used for readiness probes
- `BASE_URL`: Alpaca endpoint, such as the paper or live API URL
- `PAPER_TRADING`: keeps runtime in paper mode when truthy
- `LIVE_TRADING_ENABLED`: required before guarded live trading can proceed
- `LIVE_RUN_CONFIRMATION`: must match `LIVE_CONFIRMATION_TOKEN` for live readiness
- `LIVE_CONFIRMATION_TOKEN`: confirmation phrase expected for live readiness
- `SYMBOLS`: comma-separated stock and crypto symbols to validate
- `DECISION_LOG_PATH`, `FILL_LOG_PATH`, `DAILY_SNAPSHOT_PATH`: runtime log targets to verify

Offline development switches:

- `OFFLINE_NEWS_ENABLED`: enables local/cached news fixtures for backtests only
- `OFFLINE_NEWS_DIR`: local fixture directory, defaulting to `data/offline_news`

## Offline Backtest Flow

1. Prepare local/cached news fixture data for the configured symbol and date range.
2. Enable offline development mode.

```powershell
$env:OFFLINE_NEWS_ENABLED='true'
$env:OFFLINE_NEWS_DIR='data/offline_news'
```

3. Run a quick backtest:

```powershell
tradingbot --mode backtest --quick-backtest --quick-days 10
```

4. Confirm decision evidence identifies whether each sentiment input came from external news, local fixture data, or neutral fallback.

## Validation Commands

```powershell
python -m pytest tests/unit/test_preflight_readiness.py
python -m pytest tests/unit/test_offline_news_fixtures.py
python -m pytest tests/unit/test_log_path_readiness.py
python -m pytest tests/unit/test_model_fallback.py
python -m pytest tests/smoke/test_preflight_entrypoint.py
python -m pytest tests/smoke/test_paper_mode_guardrails.py
```

## Expected Outcomes

- Preflight completes in under 30 seconds for normal local checks.
- Missing Alpaca News access is visible but does not crash offline-capable backtests.
- Live readiness fails when required live safeguards are incomplete.
- Local fixture gaps are reported before neutral fallback is used.

## Phase 6 Validation Snapshot

Latest local validation:

- Targeted pytest suite: `25 passed`
- Paper preflight: `warning`, exit code `1`, due only to missing optional FinBERT packages (`transformers`, `torch`)
- Live preflight: `fail`, exit code `2`, because `PAPER_TRADING` is enabled
- Required dependencies: pass
- Saved model loadability: pass
- Alpaca trading, market data, and news probes: pass
