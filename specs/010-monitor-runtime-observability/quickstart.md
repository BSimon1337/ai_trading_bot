# Quickstart: Monitor Runtime Observability

## Goal

Validate that the dashboard becomes a trustworthy observability surface for mixed stock and crypto managed runtimes, including reconciled runtime truth, symbol-scoped warning visibility, order-lifecycle visibility, and correct provisional-versus-confirmed portfolio state.

## Preconditions

- Existing runtime-manager and interactive-controls features are available.
- The monitor can already launch and control local managed runtimes.
- The runtime registry path is configured.
- At least one stock symbol and one crypto symbol are available for validation.
- Terminal output remains available as a cross-check during this feature's implementation, but the dashboard should be able to explain the same outcomes.

## Suggested Symbols

- Stock symbol: `SPY`
- Crypto symbols: `BTC/USD`, `ETH/USD`

## Launch The Monitor

Use the local launcher:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\start_monitor.ps1 -Mode live -Symbols "SPY,BTC/USD,ETH/USD"
```

Open:

```text
http://127.0.0.1:8080
```

## Runtime Truth Validation

1. Start `BTC/USD` from the dashboard and confirm the card moves through startup into reconciled running state.
2. Stop `BTC/USD` and confirm the card reflects stopped state even if older trading evidence remains on disk.
3. Restart `BTC/USD`, then hard-stop the child process outside the dashboard.
4. Refresh the dashboard and confirm the card no longer presents the bot as healthy running state.
5. Repeat the same flow for `SPY` and confirm stock and crypto cards use the same runtime-mode semantics.

## Event And Warning Validation

1. Start `ETH/USD` and wait through initialization and at least one trading iteration.
2. Confirm the card shows recent runtime milestones such as startup, ready state, or recent iteration activity.
3. Trigger or reuse a known warning scenario, such as malformed evidence or a broker warning already present in logs.
4. Confirm the relevant symbol card shows that warning within the next refresh cycle instead of leaving it terminal-only.
5. Confirm a symbol with no current warning does not inherit another symbol's warning state.

## Portfolio-State Isolation Validation

1. Start a mixed set of symbols where at least one symbol fills before its next snapshot.
2. Refresh the dashboard immediately after the fill.
3. Confirm the filled symbol shows a clearly labeled provisional position state instead of a false zero-held state.
4. Confirm another symbol does not show the same held value or cash state unless its own evidence supports that value.
5. Confirm the dashboard remains correct after the next snapshot lands and provisional labeling clears naturally.
6. Confirm symbols that looked correct before startup do not regress into duplicated held-value or cash displays after the managed runtimes become active.
7. Confirm `Account Cash` remains an account-overview concept while each symbol's `Held Value` stays symbol-scoped.

## Validation Commands

Run the focused validation bundle:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m pytest tests/unit/test_monitor_data.py tests/unit/test_runtime_manager.py tests/unit/test_tray_state.py tests/contract/test_dashboard_monitor_contract.py tests/contract/test_tray_monitor_contract.py tests/smoke/test_monitor_entrypoint.py tests/smoke/test_runtime_manager_entrypoint.py
```

## Expected Evidence

- Dashboard cards that agree with actual managed runtime state after start, stop, restart, and unexpected exit
- Live or paper badges that remain consistent across stock and crypto symbols
- Recent runtime event summaries that explain what each bot just did
- Symbol-scoped warning visibility for broker/runtime/evidence issues
- Provisional portfolio labeling when fills are newer than snapshots
- `Account Cash` wording that stays account-level without leaking account totals into another symbol's held-value field
- No cross-symbol leakage of held quantity, held value, or cash state after bots are started
- No regression where pre-start card values look correct but become duplicated or overwritten once the runtimes enter active state
- Tray summary that remains consistent with dashboard runtime truth
