# Research: Modular Multi-Asset Trading Bot

## Decision 1: Use Python 3.10 as the target runtime

- **Decision**: Standardize the refactor around Python 3.10.
- **Rationale**: The user explicitly requested Python 3.10. It is mature, widely supported by
  the current data and trading ecosystem, and keeps typing/dataclass ergonomics without forcing
  newer-runtime-only features.
- **Alternatives considered**:
  - Python 3.13: Matches the current local interpreter but diverges from the requested target.
  - Python 3.11/3.12: Viable, but not aligned with the explicit requirement.

## Decision 2: Preserve Lumibot and Alpaca integration behind an execution boundary

- **Decision**: Keep Lumibot for strategy runtime orchestration and Alpaca for paper/live broker
  access, but isolate them inside execution and strategy adapter modules.
- **Rationale**: This preserves current behavior while reducing coupling between domain logic and
  third-party runtime objects. It also makes signal and risk logic easier to unit test without a
  live broker context.
- **Alternatives considered**:
  - Replace Lumibot: Higher migration risk and outside scope.
  - Keep direct imports spread across files: Lower short-term effort but poor testability.

## Decision 3: Use a functional module package instead of more root-level scripts

- **Decision**: Move domain logic into a `tradingbot/` package with modules for config,
  data/news, sentiment, strategy, risk, execution, and app entrypoints.
- **Rationale**: The requested split maps cleanly to the current responsibilities already visible
  in `config.py`, `data_handler.py`, `finbert_utils.py`, `strategy.py`, `portfolio.py`, and
  `tradingbot.py`. Packaging them clarifies ownership and reduces circular dependencies.
- **Alternatives considered**:
  - Keep root-level modules and rename files only: Does not materially improve boundaries.
  - Separate multiple services/apps: Too complex for the current repo and operator workflow.

## Decision 4: Environment variables remain the single control plane for credentials and modes

- **Decision**: All credentials, paper/live mode flags, live-enable guardrails, and run-time
  switches remain environment-variable driven.
- **Rationale**: The current project already loads settings from `.env` and `env/.env`. Keeping
  one configuration style reduces operator confusion and supports safe deploy/runtime changes
  without code edits.
- **Alternatives considered**:
  - Mixed CLI flags plus env vars: More flexible but easier to misconfigure.
  - Config files with secrets: Higher secret-management risk for this repo style.

## Decision 5: Live mode uses fail-closed two-step activation

- **Decision**: Live trading requires both a persistent live-enable environment setting and a
  separate per-run confirmation value before broker execution is allowed.
- **Rationale**: This directly reflects the clarified requirement and supports autonomous trading
  only after deliberate operator intent.
- **Alternatives considered**:
  - Single live flag: Too easy to enable accidentally.
  - Per-trade approval: Conflicts with the requirement to still behave like a bot.

## Decision 6: Failure handling differs by execution mode

- **Decision**: Live mode fails closed on missing credentials, stale data, failed guardrails, or
  execution preflight errors. Paper and backtest modes may skip affected symbols or degrade
  gracefully when safe, but they must log the failure cause and continue only when guardrails are
  still satisfied.
- **Rationale**: Real-money safety must dominate in live mode, while research and paper workflows
  benefit from controlled partial progress.
- **Alternatives considered**:
  - Stop everything on any failure: Safe but too disruptive for research workflows.
  - Best-effort continue in live mode: Unsafe for real-money trading.

## Decision 7: Testability centers on pure signal and sizing functions

- **Decision**: Extract signal-generation and position-sizing logic into pure or nearly pure
  functions/classes with `pytest` unit tests.
- **Rationale**: These are the highest-leverage logic areas for deterministic testing and match the
  user's requested coverage.
- **Alternatives considered**:
  - End-to-end only testing: Too slow and brittle for daily development.
  - Mock-heavy testing of the entire Lumibot runtime: Higher setup cost with less clarity.

## Decision 8: Daily trading performance constraints should be explicit

- **Decision**: Use the following planning targets:
  - startup preflight and mode validation: <= 30 seconds
  - per-run daily decision cycle across configured symbols: <= 60 seconds
  - smoke backtest for a representative sample: <= 5 minutes
- **Rationale**: These targets are realistic for a file-based, daily-trading-oriented bot and give
  us measurable expectations for planning and validation.
- **Alternatives considered**:
  - No explicit performance targets: Leaves daily trading readiness underspecified.
  - Aggressive sub-second targets: Unnecessary for daily trading and likely unrealistic with market
    data and sentiment inputs.
