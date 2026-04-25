# Quickstart: Monitor Accuracy Refinement

## Goal

Validate that the local monitor shows trustworthy current state, cleaner operator signals, and safe handling of mixed historical evidence.

## Prerequisites

- Python 3.10 virtual environment is available.
- Existing project dependencies are installed.
- The current monitor feature is already present and launchable.
- Local runtime evidence exists or fixture evidence can be generated for mixed current/historical scenarios.

## Start the Monitor

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Validate Current-State Trust

Use mixed evidence where a bot previously failed and then restarted successfully.

Expected result:

- The restarted bot shows its current live or paper state.
- The bot is not still marked failed solely because of older failed evidence.
- Account overview shows one internally consistent cash/equity/day PnL snapshot.

## Validate Activity Clarity

Use evidence where bots have mixed behaviors:

- one recent fill
- one recent hold/decision
- one broker rejection
- one informational negative day PnL note

Expected result:

- Dashboard shows last decision time and last fill time per bot.
- Broker rejection counts appear on the affected instance.
- Informational notes are separated from actionable issues.

## Validate Held-Value Fallback

Use a symbol with non-zero position quantity but no recent fill in the current log window.

Expected result:

- Held quantity remains visible.
- Held value stays populated when a trusted fallback valuation source exists.
- If no trusted valuation source exists, held value is explicitly unavailable rather than incorrectly shown as zero.

## Validate Historical Evidence Hygiene

Use mixed current evidence plus older malformed or archived evidence files.

Expected result:

- Current monitor view remains readable.
- Historical malformed or failed files do not dominate the active state.
- Historical evidence remains available for manual inspection outside the active monitor summary.

## Retention and Archival Guidance

The monitor now treats evidence under archive-like path segments such as `archived`, `archive`, `history`, `historical`, `old`, or `retained` as historical-only context. That evidence can still appear in the bounded historical preview, but it no longer overrides the current live or paper state.

Recommended operating pattern:

- Keep current bot evidence in the normal `logs/paper_validation*` paths.
- Move older evidence into clearly named archive folders instead of deleting it.
- If you need custom archive markers, set `MONITOR_ARCHIVE_MARKERS` as a comma-separated list.
- If you need to tighten or loosen current-state freshness, set `MONITOR_STALE_AFTER_MINUTES`.
- If you want a shorter or longer historical preview, set `MONITOR_HISTORICAL_ISSUE_LIMIT`.

Example:

```powershell
$env:MONITOR_STALE_AFTER_MINUTES="180"
$env:MONITOR_HISTORICAL_ISSUE_LIMIT="5"
$env:MONITOR_ARCHIVE_MARKERS="archived,history,old"
```

Expected result:

- Current dashboards stay focused on active evidence.
- Archived failures remain visible only in the historical context section.
- Tray severity follows current issues, not retained historical noise.

## Automated Validation

Run:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m pytest tests/unit/test_monitor_data.py tests/unit/test_tray_state.py tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/smoke/test_monitor_entrypoint.py
```

Expected result:

- Tests pass.
- Current-state precedence, held-value fallback, issue-vs-note separation, and retention behavior are covered.

## Safety Check

Expected result:

- Dashboard and tray remain read-only.
- No order placement, order cancellation, or live-approval behavior is introduced by this refinement.
