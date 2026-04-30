# Research: Monitor Runtime Observability

## Decision 1: Normalize observability from existing runtime registry and evidence files

**Decision**: Build a normalized symbol observability view inside the existing monitor pipeline by merging runtime-registry state, symbol-scoped decision/fill/snapshot evidence, and monitor-detected warning conditions at request time.

**Rationale**: The monitor already owns the dashboard payload and the runtime manager already owns lifecycle truth. Reusing those two inputs avoids the complexity of a second persistence layer while still letting the UI see more than the raw CSV fields currently expose.

**Normalization responsibilities**:

- Reconcile managed runtime state with actual process existence before card rendering.
- Summarize recent lifecycle milestones into a lightweight operator-facing event stream rather than exposing terminal output verbatim.
- Extract symbol-scoped warning conditions from runtime reconciliation, malformed evidence reads, broker anomalies, and monitor freshness checks.
- Preserve one dashboard model for both stock and crypto symbols.

**Alternatives considered**:

- **New event log store or database**: Rejected because it adds a second truth source and more operational complexity than the current local app needs.
- **Raw terminal tail inside the UI**: Rejected because it is noisy, difficult to test, and would blur operator-facing state with developer-facing logs.

## Decision 2: Prefer symbol-local effective portfolio state with explicit provenance

**Decision**: Derive each card's effective portfolio state independently, with explicit provenance that distinguishes confirmed snapshot values from provisional fill-derived reconstruction.

**Rationale**: The recent value-leak and zero-held-after-fill behaviors showed that portfolio state can become misleading when the monitor tries to merge evidence too loosely or at the wrong scope. A symbol-local calculation path with explicit provenance is the safest way to preserve card truth.

**State-precedence rules**:

- Use the latest valid symbol-local snapshot as the confirmed portfolio state when it is current.
- If a fresher filled order exists after the latest valid snapshot, derive a provisional delta state for that same symbol only.
- Never reuse one symbol's snapshot or fill-derived totals as another symbol's card-level held value.
- Preserve account-level overview as a separate aggregate concern rather than letting it bleed into per-symbol holdings.
- Preserve correct pre-start symbol values when runtime state transitions to active, so startup does not overwrite a card with another symbol's evidence.

**Alternatives considered**:

- **Snapshot only**: Rejected because it produces false zero-held states immediately after fresh fills.
- **Fill-only position inference**: Rejected because it can drift from confirmed broker or snapshot truth and is insufficient for stable longer-lived display.

## Decision 3: Surface warnings and lifecycle states as operator-focused summaries

**Decision**: Present warnings and order/runtime lifecycle as concise operator summaries rather than raw log lines, but keep them close enough to source conditions that troubleshooting remains grounded.

**Rationale**: The user needs to understand what happened without tailing a console, but the dashboard should not become an unreadable firehose. Operator-focused summaries preserve trust while staying testable and consistent.

**Operator-facing categories**:

- **Runtime lifecycle**: starting, ready, iterating, stopping, stopped, failed, exited unexpectedly
- **Order lifecycle**: no recent order, submitted, pending broker acknowledgement, new, partial fill, filled, canceled, rejected
- **Warnings**: broker warning, malformed evidence, stale evidence, stale market data, runtime reconciliation warning
- **Freshness**: current, provisional, stale, historical, unavailable

**Alternatives considered**:

- **Only show final action labels**: Rejected because it hides too much of the path between click and outcome.
- **Show raw broker/runtime messages unchanged**: Rejected because many messages are too noisy or too implementation-specific for a dashboard card.

## Decision 4: Standardize badge and wording precedence across stock and crypto

**Decision**: Define one precedence model for card badges and field wording that prefers known mode context and reconciled runtime truth over generic inferred status.

**Rationale**: The previous `RUNNING` vs `LIVE`, `paper` bleed-through, and "unknown" mode behaviors made equivalent states look different across symbols. One precedence model is necessary so a stock card and a crypto card mean the same thing when they are in the same state.

**Precedence expectations**:

- Known managed `live` or `paper` mode should outrank generic `running` as the top card badge.
- Reconciled managed runtime state should outrank stale historical log inference.
- "Unavailable", "historical", "provisional", and "stale" should be reserved for distinct evidence conditions instead of used interchangeably.
- Symbols with no fresh decision or fill evidence should still render coherent runtime truth when the runtime manager knows they are active.

**Alternatives considered**:

- **Asset-specific badge semantics**: Rejected because it trains the operator to interpret two subtly different dashboards.
- **Mostly log-derived badge semantics**: Rejected because it recreates the stale and misleading runtime-status problems we already saw.
