# Research: Sentiment Observability

## Decision: Reuse Existing Decision-Log Sentiment Fields as the Current Snapshot Source

**Decision**: Use the latest decision evidence per symbol as the primary current sentiment snapshot because it already captures `sentiment_label`, `sentiment_probability`, and `sentiment_source` alongside runtime activity.

**Rationale**: The monitor already trusts decision rows as the per-bot current-state source. Reusing that path keeps sentiment visibility aligned with the actual trading iteration that produced the latest action or hold reason.

**Alternatives considered**:

- **Query FinBERT directly from the monitor**: Rejected because it adds a new runtime responsibility to the monitor and breaks the local-evidence pattern.
- **Read sentiment only from strategy memory with no persisted evidence**: Rejected because it would disappear across restarts and weaken observability.

## Decision: Extend News Handling to Surface Bounded Headline Evidence

**Decision**: Reuse `DataHandler.get_news_records()` and extend the runtime evidence path so the monitor can show a bounded set of recent headlines, headline counts, and freshness metadata per symbol.

**Rationale**: The repository already fetches and normalizes news records for Alpaca and offline fixtures. Exposing a bounded preview gives operators and class reviewers a clear explanation of why the sentiment state exists without requiring raw CSV or terminal inspection.

**Alternatives considered**:

- **Show only the sentiment label with no headline context**: Rejected because it hides the evidence behind the NLP output.
- **Dump all recent headlines into the dashboard**: Rejected because it would clutter the UI and make refresh behavior noisy.

## Decision: Distinguish Real Neutral Sentiment from Fallback Neutral State

**Decision**: Represent fallback-driven neutral sentiment explicitly as a separate operator-visible availability state even if the final label remains `neutral`.

**Rationale**: This project already falls back to neutral sentiment when FinBERT dependencies fail or when Alpaca/offline news cannot produce usable headlines. Operators need to know whether “neutral” came from actual model scoring or from a fail-safe path.

**Alternatives considered**:

- **Treat all neutral values as equivalent**: Rejected because it hides model availability and data quality issues.
- **Escalate fallback to a hard monitor issue**: Rejected because fallback is often expected behavior and should remain readable without over-alerting.

## Decision: Keep Sentiment History Short and Dashboard-Bounded

**Decision**: Show only a short recent sentiment trend per symbol using bounded history, counts, and preview fields rather than storing or rendering an unbounded textual timeline.

**Rationale**: Operators need trend direction and recent context, not a full news archive in the dashboard. Bounded previews preserve readability and keep refresh costs stable.

**Alternatives considered**:

- **No sentiment history at all**: Rejected because it makes it hard to tell whether sentiment is stable, changing, or stale.
- **Long-form historical text on the main card**: Rejected because it would overwhelm the monitor layout.

## Decision: Preserve Read-Only Monitor Behavior

**Decision**: Keep sentiment observability inside the existing monitor and tray payloads without introducing any control-plane behavior, broker calls for execution, or interactive strategy changes.

**Rationale**: This feature’s purpose is explainability. Mixing it with runtime controls would increase scope and safety risk and blur the current architecture plan.

**Alternatives considered**:

- **Combine sentiment observability with interactive strategy tuning**: Rejected because runtime control deserves its own dedicated safety-focused feature.

## Validation Outcome: No New Dependencies Or Control-Plane Behavior Were Needed

**Decision**: Keep the implementation inside the existing Flask/template monitor, CSV runtime evidence, and tray read-only surface with no additional packages and no interactive trading controls.

**Rationale**: The existing monitor path was already flexible enough to carry sentiment snapshot fields, bounded headline previews, and short trend history. Extending that path preserved the repo's local-operator workflow and avoided mixing observability work with runtime-control design.

**Confirmed impact**:

- No new Python dependencies were introduced for sentiment observability.
- The tray menu remains limited to opening the dashboard, refreshing status, and exiting the monitor.
- No broker execution, approval, cancellation, or strategy-tuning behavior was added as part of this feature.
