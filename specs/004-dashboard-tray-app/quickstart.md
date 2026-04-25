# Quickstart: Dashboard and Tray App

## Goal

Run a local read-only monitor that shows trading bot status in a browser dashboard and presents a system tray item while the monitor is active.

## Prerequisites

- Python 3.10 virtual environment is available.
- Project dependencies are installed.
- Existing bot runtime logs may exist, but the monitor must also handle no-data states.
- Live trading does not need to be enabled to run the monitor.

## Install Tray Dependencies

Install pinned dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install pystray==0.19.5 Pillow==11.3.0
```

## Run the Browser Dashboard

From the repository root:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe monitor_app.py
```

Open:

```text
http://localhost:8080
```

Expected result:

- Dashboard loads without requiring live trading.
- Missing logs show no-data or warning states.
- Existing logs show status cards, recent decisions, and recent fills.

## Run the Tray Monitor

Package entrypoint:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\tradingbot-monitor.exe
```

Module form:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray
```

Expected result:

- Tray item appears within 10 seconds on supported desktops.
- Tray menu includes Open Dashboard, Refresh Status, and Exit Monitor.
- Open Dashboard opens `http://localhost:8080` or the configured dashboard URL.
- Exit Monitor closes the monitor/tray process only.

## Run Dashboard Only

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8080 --refresh-seconds 15
```

Expected result:

- Dashboard starts without creating a tray icon.
- The terminal remains attached to the Flask process until `Ctrl+C`.
- Monitoring remains read-only.

## Verify Read-Only Safety

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/unit/test_monitor_data.py tests/unit/test_tray_state.py tests/smoke/test_monitor_entrypoint.py
```

Expected result:

- Tests pass.
- Dashboard/tray contracts do not call trading order APIs.
- Credential values are not present in dashboard or tray output.

## Verify Fixture States

Use fixture logs for:

- healthy running
- paper
- active live
- blocked live
- stale data
- malformed CSV
- no data
- broker rejection

Expected result:

- Each fixture state maps to the correct dashboard and tray status.

## Stop the Monitor

From tray:

```text
Exit Monitor
```

From terminal:

```text
Ctrl+C
```

Stopping the monitor should not stop separately running trading bot processes.

## Validation Notes

Observed automated validation for this feature phase:

- `tests/smoke/test_monitor_entrypoint.py`
- `tests/contract/test_dashboard_monitor_contract.py`
- `tests/contract/test_tray_monitor_contract.py`
- `tests/unit/test_monitor_data.py`
- `tests/unit/test_tray_state.py`
- full `pytest` suite: `73 passed, 1 warning`

Observed local launch validation on 2026-04-25:

- Started `python -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8093`
- Confirmed `GET /health` returned HTTP 200 with monitor state payload
- Stopped the monitor process without touching trading bot processes

Observed read-only safety review:

- `tradingbot/app/monitor.py` and `tradingbot/app/tray.py` contain no order-placement, order-cancel, or trade-approval calls
- Monitor actions are limited to dashboard rendering, tray refresh, browser open, and monitor exit behavior
