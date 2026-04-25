# Preflight and Offline Mode CLI Contract

## Purpose

Define the operator-facing command behavior for readiness validation and offline/cached news backtesting.

## Entrypoint

The package CLI exposes a preflight-capable command through the existing trading bot runner.

## Commands

### Preflight Readiness

```text
tradingbot --mode preflight
```

**Inputs**

- environment-driven credentials and mode switches
- configured symbol list
- configured log paths
- optional offline development mode flag or environment setting
- optional fixture directory setting

**Required checks**

- credentials are present
- Alpaca trading access check is reported
- Alpaca market data/news access check is reported separately
- configured symbols are parseable and classified
- log paths are writable or creatable
- live safeguards are satisfied when live readiness is requested
- required dependencies are importable
- optional model and local sentiment capabilities are diagnosed

**Outputs**

- human-readable readiness summary
- stable process exit code
- log entry containing the same overall status and check messages

**Exit codes**

- `0`: overall status is pass
- `1`: overall status is warning
- `2`: overall status is fail

### Backtest With Offline News

```text
tradingbot --mode backtest --quick-backtest --quick-days 10
```

When offline development mode is enabled, the backtest uses local/cached fixture data before neutral fallback.

**Expected behavior**

- valid local fixtures provide headlines for matching symbols and date windows
- fixture gaps are reported and fall back to neutral sentiment only for missing coverage
- external news failures do not crash offline-capable backtests
- decision evidence records whether external, local fixture, or neutral fallback sentiment was used

## Safety Rules

- Offline development mode must not satisfy live-trading readiness.
- Live mode must still fail closed when live safeguards are incomplete.
- Missing or unauthorized external news access must remain operator-visible.
- Optional dependency warnings must not be confused with required dependency failures.
