# Data Model: Preflight Validation and Offline Development Mode

## ReadinessCheckResult

- **Purpose**: Captures the outcome of one pre-run validation check.
- **Fields**:
  - `name`: stable check identifier
  - `category`: `credentials | data_access | model | dependency | log_path | symbol | safeguard | fixture`
  - `status`: `pass | warning | fail`
  - `message`: operator-facing explanation
  - `remediation`: recommended action
  - `details`: optional structured context for logs or tests
- **Validation**:
  - status must be one of the canonical values
  - fail and warning results must include remediation text
  - category must map to a known readiness area

## ReadinessReport

- **Purpose**: Summarizes whether a run is ready to start.
- **Fields**:
  - `timestamp`
  - `mode`: `backtest | paper | live | preflight`
  - `symbols`: configured symbols
  - `overall_status`: `pass | warning | fail`
  - `checks`: list of `ReadinessCheckResult`
  - `offline_mode_enabled`: boolean
- **Relationships**:
  - contains many `ReadinessCheckResult` items
- **Validation**:
  - overall status must equal the most severe check status
  - live mode must fail if live safeguards fail
  - offline mode must not downgrade live-safeguard failures

## OfflineNewsFixture

- **Purpose**: Represents local/cached news available for backtest sentiment inputs.
- **Fields**:
  - `symbol`
  - `timestamp`
  - `headline`
  - `source`: fixture source label
  - `url`: optional reference
  - `quality_status`: `valid | malformed | out_of_range | empty`
- **Validation**:
  - symbol and headline must be non-empty for valid rows
  - timestamps must be parseable and comparable to the requested backtest range
  - malformed rows must be reported rather than crashing the run

## SentimentDataSourceStatus

- **Purpose**: Records which news/sentiment source was used for an evaluated decision.
- **Fields**:
  - `symbol`
  - `window_start`
  - `window_end`
  - `source_type`: `external | local_fixture | neutral_fallback`
  - `headline_count`
  - `fallback_reason`
- **Relationships**:
  - associated with decision records and sentiment snapshots
- **Validation**:
  - `neutral_fallback` requires a non-empty fallback reason
  - `local_fixture` requires fixture coverage details

## DependencyDiagnostic

- **Purpose**: Describes availability of required and optional packages or runtime capabilities.
- **Fields**:
  - `name`
  - `required`: boolean
  - `status`: `available | missing | incompatible`
  - `impact`
  - `remediation`
- **Validation**:
  - missing required dependencies produce readiness failure
  - missing optional dependencies produce warnings unless a requested mode requires them
