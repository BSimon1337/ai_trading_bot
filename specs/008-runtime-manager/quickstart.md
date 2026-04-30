# Quickstart: Runtime Manager

## Goal

Validate that the application can own bot lifecycle locally without relying on manual multi-window shell management.

## Prerequisites

- Python 3.10 virtual environment is available.
- Existing project dependencies are installed.
- Current monitor feature is already working.
- Bot symbols and environment-backed config are already available for paper or live runs.

## Start The Monitor

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Validate Runtime Start

Use the runtime-manager entrypoint to start one symbol.

Example:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.main --mode runtime-start --managed-symbol BTC/USD
```

Expected result:

- The symbol runtime launches without opening a manual PowerShell workflow.
- The runtime registry records the symbol as running.
- The dashboard shows the symbol as an active managed runtime with a fresh session.
- Symbol-scoped decision, fill, and snapshot files continue updating normally.
- The runtime registry file remains readable on disk and does not expose credentials.

## Validate Multi-Symbol Tracking

Start more than one configured symbol runtime.

Example:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.main --mode runtime-start --managed-symbol BTC/USD --managed-symbol ETH/USD
```

Expected result:

- Each symbol shows an independent runtime state.
- One symbol stopping or failing does not incorrectly change another symbol’s runtime state.
- The monitor still shows shared account context while keeping runtime ownership per symbol.

## Validate Stop And Restart

Stop one active symbol, then restart it.

Example:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.main --mode runtime-stop --managed-symbol BTC/USD
.\.venv\Scripts\python.exe -m tradingbot.app.main --mode runtime-restart --managed-symbol BTC/USD
```

Expected result:

- The stop action transitions the symbol to stopped cleanly.
- Restart creates a new runtime session and fresh process ownership.
- Older failures or stopped sessions do not remain the active runtime state after the restart.
- The runtime registry preserves recent session history while showing only one authoritative current runtime for the symbol.

## Validate Live Safety

Attempt a live-mode runtime start using the same configuration expectations currently required for live trading.

Example expectation:

- if `PAPER_TRADING=0` and the live confirmation inputs are missing or mismatched, `runtime-start` should fail closed and write a readable failed runtime state
- if the live confirmation inputs are valid, the managed runtime may proceed and should still remain one process per symbol

Expected result:

- Live runtime actions remain explicit and guarded.
- The runtime manager does not bypass current live-safety behavior.
- Failed live starts surface a readable reason instead of leaving ghost running state.

## Automated Validation

Run:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m pytest tests/unit/test_runtime_manager.py tests/unit/test_monitor_data.py tests/unit/test_tray_state.py tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/smoke/test_runtime_manager_entrypoint.py tests/smoke/test_monitor_entrypoint.py
```

Expected result:

- Tests pass.
- Runtime-manager registry behavior, lifecycle transitions, monitor payload shaping, and launch-path safety are covered.

## Fixture Guidance

Recommended setup for implementation and validation:

- keep using existing symbol-scoped decision, fill, and snapshot fixture files
- add runtime-registry fixture files with mixed `running`, `stopped`, `failed`, and `restarted` symbol sessions
- prefer one fixture set where the registry says a symbol is stopped while older CSV evidence still exists, so the monitor contract is forced to distinguish stopped versus merely stale
- prefer one fixture set where a restart creates a new session for the same symbol, so fresh-session precedence can be validated explicitly

## Manual Validation Notes

Expected manual checks for implementation:

- Start one symbol and confirm a running runtime session appears in the monitor.
- Stop that symbol and confirm it becomes stopped instead of merely stale.
- Restart that symbol and confirm the fresh runtime session overrides the old one.
- Start multiple symbols and confirm each shows the correct independent runtime state.
- Confirm no credentials appear in runtime-manager registry or monitor payloads.
- Confirm that a stopped symbol remains visible in the monitor instead of silently disappearing.
- Confirm that a fresh restarted runtime does not inherit an older failed status from pre-restart CSV evidence.
