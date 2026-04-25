# Quickstart: Dashboard and Tray App

## Goal

Run a local read-only monitor that shows trading bot status in a browser dashboard and presents a system tray item while the monitor is active.

## Prerequisites

- Python 3.10 virtual environment is available.
- Project dependencies are installed.
- Existing bot runtime logs may exist, but the monitor must also handle no-data states.
- Live trading does not need to be enabled to run the monitor.

## Install Planned Tray Dependencies

When this feature is implemented, install pinned dependencies:

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

Planned command:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray
```

Expected result:

- Tray item appears within 10 seconds on supported desktops.
- Tray menu includes Open Dashboard, Refresh Status, and Exit Monitor.
- Open Dashboard opens `http://localhost:8080` or the configured dashboard URL.
- Exit Monitor closes the monitor/tray process only.

## Verify Read-Only Safety

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py
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
