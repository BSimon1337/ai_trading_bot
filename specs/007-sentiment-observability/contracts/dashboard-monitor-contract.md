# Dashboard Monitor Contract: Sentiment Observability

## Routes Reused

- `GET /`
- `GET /health`
- `GET /api/status`

## `/api/status` Payload Additions

### Top-Level

The existing dashboard payload remains intact. Sentiment observability extends per-instance fields and may add bounded monitor-level sentiment summary collections if needed for rendering, but the primary contract change is per monitored instance.

### Per-Instance Additions

Each `instances[]` entry must expose sentiment-facing fields in a read-only form:

- `sentiment_label`
- `sentiment_probability`
- `sentiment_source`
- `sentiment_availability_state`
- `sentiment_is_fallback`
- `sentiment_last_updated_utc`
- `headline_count`
- `headline_preview`
- `sentiment_trend`
- `sentiment_headline_source_window`

### Field Semantics

- `sentiment_label`: Latest operator-visible sentiment label for the symbol.
- `sentiment_probability`: Latest confidence/probability associated with the label when available.
- `sentiment_source`: Where the sentiment input came from, such as external news, local fixture, or neutral fallback.
- `sentiment_availability_state`: Readable explanation of whether the sentiment is real, fallback-driven, unavailable, or stale.
- `sentiment_is_fallback`: Boolean flag to distinguish fallback-neutral state from real neutral scoring.
- `sentiment_last_updated_utc`: Timestamp of the latest sentiment evidence used for display.
- `headline_count`: Number of recent headlines analyzed for the current bounded view.
- `headline_preview`: Bounded list of recent headline strings or structured headline preview rows.
- `sentiment_trend`: Bounded recent sentiment history suitable for dashboard rendering.
- `sentiment_headline_source_window`: Readable description of the time window used for the current sentiment headline context when available.

### Evidence Alignment Expectations

- `sentiment_label`, `sentiment_probability`, and `sentiment_source` should stay aligned with the latest trusted decision/runtime evidence for the symbol.
- Headline preview and trend fields may be assembled from bounded supporting evidence, but they must not contradict the displayed current sentiment snapshot.
- Fallback-neutral sentiment must remain distinguishable from real neutral scoring in both raw payload fields and rendered dashboard text.

## Rendering Expectations

- The main dashboard must show sentiment state per symbol without requiring raw log inspection.
- Detail views must show bounded headline previews and recent sentiment trend context.
- Missing or fallback-only sentiment evidence must remain readable and must not crash the page.
- The feature must preserve read-only behavior and must not add trade-control UI actions.
