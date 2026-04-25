# Research: Preflight Validation and Offline Development Mode

## Decision 1: Add preflight as a first-class CLI mode

- **Decision**: Extend the existing package CLI with a preflight/readiness command rather than creating a separate script or dashboard-only workflow.
- **Rationale**: Operators already use the command line for backtests and live/paper startup. A CLI mode can be tested deterministically, used in automation, and run before any trading runtime starts.
- **Alternatives considered**:
  - Dashboard-only readiness: useful for monitoring but less reliable for pre-run automation.
  - Separate root script: quick to add but inconsistent with the packaged app entrypoint.

## Decision 2: Use pass/warning/fail readiness semantics

- **Decision**: Each readiness check returns `pass`, `warning`, or `fail`, and the report computes an overall status from the most severe item.
- **Rationale**: Some issues should block runtime, while others should be visible but non-fatal in offline backtests. This avoids treating optional model dependencies and live-trading guardrail failures as the same severity.
- **Alternatives considered**:
  - Boolean pass/fail only: too coarse for optional features and backtest fallbacks.
  - Freeform text only: harder to test and automate.

## Decision 3: Keep offline mode scoped to backtests and local validation

- **Decision**: Offline development mode can supply local/cached news only for backtesting and local validation flows.
- **Rationale**: Offline news is helpful while Alpaca News is unavailable, but it must not create the impression that live trading has fresh market news. Live readiness remains dependent on current external access and guardrails.
- **Alternatives considered**:
  - Allow offline news in live mode: unsafe and potentially misleading.
  - Disable strategy development until external news works: unnecessarily blocks progress.

## Decision 4: Use file-backed news fixtures

- **Decision**: Use local file fixtures for offline news input, organized by symbol and date/headline fields.
- **Rationale**: File fixtures match the repository's existing file-backed data/log style and are easy to inspect, commit when sanitized, or generate later.
- **Alternatives considered**:
  - SQLite or a service cache: more infrastructure than needed.
  - In-code fixtures: hard to maintain and not operator-friendly.

## Decision 5: Preserve current dependency set

- **Decision**: Implement the base feature without new dependencies.
- **Rationale**: The project just added pinned dependency files. The readiness report can use standard library checks plus existing package imports and runtime code.
- **Alternatives considered**:
  - Add a CLI formatting library: not needed for a readable first pass.
  - Add a validation framework: overkill for a small readiness report.

## Decision 6: Report optional model/sentiment availability separately

- **Decision**: Treat saved model loadability and local FinBERT availability as optional capability checks unless a run explicitly requires those capabilities.
- **Rationale**: Backtests and paper runs can still be meaningful with fallback behavior, but operators need to know when model or local sentiment inputs are unavailable.
- **Alternatives considered**:
  - Require all optional packages for every run: increases install burden and blocks lightweight development.
  - Hide optional failures: causes confusing trading results.
