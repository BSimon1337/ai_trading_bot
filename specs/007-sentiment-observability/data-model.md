# Data Model: Sentiment Observability

## Sentiment Snapshot

**Purpose**: Represents the latest trusted per-symbol sentiment state shown in the monitor.

**Fields**:

- `symbol`
- `label`
- `probability`
- `source`
- `availability_state`
- `is_fallback`
- `observed_at`
- `decision_mode`

**Validation Rules**:

- Must come from the latest trusted decision/runtime evidence for that symbol.
- Must distinguish fallback-neutral state from real model-scored neutral state.
- Missing probability or label should render as unavailable rather than causing an error.

## Headline Evidence Preview

**Purpose**: Represents the bounded set of recent headlines used to explain a symbol’s sentiment context.

**Fields**:

- `symbol`
- `headline_count`
- `headlines`
- `source`
- `window_start`
- `window_end`
- `is_stale`

**Validation Rules**:

- Headline previews must be bounded to a small count suitable for dashboard display.
- If no headlines exist, the absence must be explicit.
- Preview text should remain readable without requiring raw log inspection.

## Sentiment Trend Entry

**Purpose**: Represents one recent sentiment observation for a symbol so the monitor can summarize short-term direction or consistency.

**Fields**:

- `timestamp`
- `label`
- `probability`
- `source`
- `availability_state`

**Validation Rules**:

- Trend entries should come from recent runtime evidence only.
- Trend output should remain bounded and not expand into an unbounded archive view.

## Sentiment Availability State

**Purpose**: Represents the operator-facing explanation of how sentiment was produced.

**Fields**:

- `state`
- `message`
- `is_actionable`

**Validation Rules**:

- Must differentiate external/news-backed scoring, local-fixture scoring, no-headline state, and neutral fallback state.
- Informational fallback states should not automatically become critical monitor failures.
