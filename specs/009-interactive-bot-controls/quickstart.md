# Quickstart: Interactive Bot Controls

## Goal

Validate that the dashboard becomes the preferred local operator surface for safely starting, stopping, and restarting managed runtimes for both a stock symbol and a crypto symbol while preserving live/paper clarity and recent control activity.

## Preconditions

- Existing runtime-manager feature is available and validated.
- Existing CLI runtime-manager commands remain available as fallback validation tools while this feature is being built.
- The local runtime registry path is configured.
- The monitor can already render managed runtime state.
- For the safest first pass, begin with paper mode where possible. Live validation should only be used after paper behavior is understood.

## Suggested Symbols

- Stock symbol: `SPY`
- Crypto symbol: `BTC/USD`

## Launch The Monitor

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\Activate.ps1
$env:SYMBOLS="SPY,BTC/USD"
$env:CRYPTO_SYMBOLS=""
$env:ALPACA_CRYPTO_UNIVERSE="none"
$env:RUNTIME_REGISTRY_PATH="logs/runtime/runtime_registry.json"
.\.venv\Scripts\python.exe -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Paper Control Validation

1. Confirm the dashboard shows both `SPY` and `BTC/USD` as managed symbols with visible control affordances.
2. Use the dashboard to start `SPY` and confirm the symbol enters a startup/running state.
3. Use the dashboard to stop `SPY` and confirm the symbol shows `stopped` rather than `stale`.
4. Use the dashboard to start `BTC/USD` and confirm the symbol enters a startup/running state.
5. Restart `BTC/USD` from the dashboard and confirm a new session identifier appears.
6. Verify recent control activity shows the stock and crypto actions with readable outcomes and timestamps.

## Live Safety Validation

1. Configure one live-capable symbol as a managed runtime target.
2. Attempt a live start or restart from the dashboard for either the stock or crypto path you plan to run live first.
3. Confirm the dashboard presents an explicit live confirmation step before execution.
4. Confirm a blocked live action returns a readable reason in the dashboard without requiring terminal inspection.

## Validation Commands

Run the focused validation bundle:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_monitor_data.py tests/unit/test_runtime_manager.py tests/unit/test_tray_state.py tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/smoke/test_monitor_entrypoint.py tests/smoke/test_runtime_manager_entrypoint.py
```

## Expected Evidence

- Dashboard buttons or forms for `start`, `stop`, and `restart`
- Visible paper vs live labeling near control actions
- Recent control activity entries for both stock and crypto actions
- Runtime state changes reflected in the dashboard after each action
- Runtime registry updates that remain readable after refresh
- CLI/runtime-manager fallback commands still work if you need to cross-check a dashboard-issued result during validation
