# Offline News Fixtures

Use this directory for local or cached news data that lets backtests run when
external news access is unavailable.

## Convention

- Keep fixtures sanitized and safe to commit.
- Prefer one file per symbol and date window when practical.
- Name files with the symbol and date range, for example
  `SPY_2024-10-22_2024-11-01.csv`.
- Include enough fields for backtest sentiment replay, such as `symbol`,
  `published_at`, `headline`, and optional `source`.
- Do not use offline fixtures to satisfy live trading readiness checks.

## Source Labels

Decision evidence should identify whether sentiment came from:

- `external`: Alpaca or another live news provider
- `local_fixture`: a local fixture in this directory
- `neutral_fallback`: no usable news was available, so the strategy used the
  neutral fallback path
