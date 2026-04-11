# Data Model: Modular Multi-Asset Trading Bot

## RunConfiguration

- **Purpose**: Canonical runtime configuration used by backtest, paper, and guarded live modes.
- **Fields**:
  - `mode`: `backtest | paper | live`
  - `symbols`: list of eligible stock/crypto symbols
  - `paper_trading`: boolean
  - `live_enabled`: boolean persistent gate
  - `live_run_confirmation`: string/boolean per-run confirmation gate
  - `cash_at_risk`: float
  - `max_position_pct`: float
  - `max_gross_leverage`: float
  - `daily_loss_limit_pct`: float
  - `max_trades_per_day`: integer
  - `cooldown_minutes_after_loss`: integer
  - `max_notional_per_order_usd`: float
  - `max_consecutive_losses`: integer
  - `max_data_staleness_minutes`: integer
  - `start_date`: date for backtests
  - `end_date`: date for backtests
  - `log_paths`: decision/fill/snapshot output locations
- **Validation**:
  - live mode requires both live gate fields present and valid
  - symbols list must be non-empty
  - risk percentages must be bounded to safe numeric ranges
  - backtest dates must be ordered correctly

## EligibleInstrument

- **Purpose**: Defines a tradable symbol under the configured run.
- **Fields**:
  - `symbol`: canonical symbol string
  - `asset_class`: `stock | crypto`
  - `market_schedule`: `NASDAQ | 24/7 | custom`
  - `enabled`: boolean
- **Relationships**:
  - many instruments belong to one `RunConfiguration`
- **Validation**:
  - symbol format must normalize consistently for the selected asset class

## SentimentSnapshot

- **Purpose**: Encapsulates the news-derived sentiment inputs for a symbol at evaluation time.
- **Fields**:
  - `symbol`
  - `window_start`
  - `window_end`
  - `headline_count`
  - `sentiment_probability`
  - `sentiment_label`
  - `average_headline_score`
- **Validation**:
  - empty headline sets are allowed but must be explicit and traceable
  - timestamps must be ordered and timezone-safe

## TradingSignal

- **Purpose**: Represents the strategy's decision candidate before execution.
- **Fields**:
  - `symbol`
  - `asset_class`
  - `action`: `buy | sell | hold | flat`
  - `action_source`: `sentiment | model | hybrid | guardrail`
  - `confidence`
  - `reason`
  - `last_price`
  - `requested_quantity`
  - `features_timestamp`
- **Relationships**:
  - generated from one `SentimentSnapshot`
  - evaluated by one `RiskDecision`
- **Validation**:
  - confidence must be numeric and bounded
  - action must be canonical across logs, tests, and monitoring

## RiskDecision

- **Purpose**: Captures the result of applying portfolio and safety rules to a trading signal.
- **Fields**:
  - `symbol`
  - `allowed`: boolean
  - `effective_quantity`
  - `block_reason`
  - `gross_leverage_estimate`
  - `breaches_daily_loss_limit`
  - `breaches_trade_frequency_limit`
  - `breaches_consecutive_loss_limit`
  - `data_stale`
- **State transitions**:
  - `proposed -> allowed`
  - `proposed -> reduced`
  - `proposed -> blocked`
- **Validation**:
  - blocked outcomes must carry a non-empty reason

## ExecutionRecord

- **Purpose**: Durable operator-facing record of what the system decided and what followed.
- **Fields**:
  - `timestamp`
  - `mode`
  - `symbol`
  - `asset_class`
  - `action`
  - `action_source`
  - `quantity`
  - `portfolio_value`
  - `cash`
  - `reason`
  - `result`: `submitted | skipped | blocked | failed`
  - `order_id` (optional)
- **Relationships**:
  - derived from one `TradingSignal` and zero or one broker submission
- **Validation**:
  - every evaluated signal must yield an execution record
  - live-mode records must show that safeguards passed before submission
