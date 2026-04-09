# CLI and Runtime Contract

## Purpose

Define the expected operator-facing runtime entrypoints and control contract for the modular
trading bot refactor.

## Entry Points

### Main App Entrypoint

- **Responsibility**: Route execution into backtest, paper, or guarded live flows
- **Inputs**:
  - environment-driven credentials
  - environment-driven mode switches
  - optional CLI flags for run selection and quick validation
- **Outputs**:
  - structured logs
  - decision CSV updates
  - fill CSV updates when execution occurs
  - process failure with clear message when safety checks fail

### Backtest Entrypoint

- **Responsibility**: Execute historical validation using the shared signal and risk pipeline
- **Contract**:
  - requires valid backtest dates and symbol configuration
  - must emit performance summary and decision evidence

### Paper Trading Entrypoint

- **Responsibility**: Run against Alpaca paper trading without live capital exposure
- **Contract**:
  - requires valid paper credentials
  - must never require live-enable guards
  - must log decisions, fills, and blocked actions

### Live Trading Entrypoint

- **Responsibility**: Run autonomous live trading only after explicit operator intent
- **Contract**:
  - requires valid live credentials
  - requires persistent live-enable setting
  - requires separate per-run confirmation value
  - must fail closed before broker submission when any safeguard is missing

## Logging Contract

- Every evaluated signal produces a decision record.
- Every broker submission attempt produces either a fill/execution record or an explicit failure/block record.
- Run mode must be visible in logs and monitoring-compatible outputs.
