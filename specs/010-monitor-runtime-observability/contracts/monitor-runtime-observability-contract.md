# Contract: Monitor Runtime Observability Integration

## Purpose

Defines the dashboard payload additions and rendering expectations required to make runtime truth, warning visibility, event visibility, and symbol-state isolation trustworthy across stock and crypto symbols.

## `GET /api/status`

**Behavior**: Returns the dashboard status model with reconciled runtime truth, normalized observability state, and symbol-isolated portfolio values for each symbol card.

**Required new or clarified instance fields**:

- `runtime_mode_context`
- `runtime_state`
- `status`
- `status_reason`
- `recent_runtime_events`
- `active_warnings`
- `latest_order_lifecycle`
- `portfolio_is_provisional`
- `held_value_source`
- `freshness_state`
- `freshness_explanation`

**Required invariants**:

- Per-symbol held quantity, held value, and cash must be derived from that symbol's own evidence path.
- Account-overview cash and equity may be shared account-level values, but they must not be mislabeled or reused as another symbol's held value.
- Known live or paper mode context must outrank generic running-state wording in card badges.
- Reconciled managed runtime truth must outrank stale historical trading evidence.
- Provisional portfolio state must be labeled explicitly.
- Startup transitions must not overwrite a symbol card with another symbol's portfolio or runtime evidence.

**Acceptance checks**:

- Refreshing after an unexpected process exit changes the reported runtime state appropriately.
- Refreshing after a fresh fill but before the next snapshot shows provisional holdings instead of a false zero-held state.
- Mixed stock/crypto cards with equivalent runtime state use equivalent badge semantics.
- No symbol card displays another symbol's held value or cash state after refresh.
- A symbol that looked correct before runtime startup still shows symbol-correct values after the runtime becomes active.

## `GET /`

**Behavior**: Returns the operator-facing dashboard with runtime truth, recent event visibility, warning visibility, and consistent field semantics.

**Required content**:

- per-symbol reconciled runtime status
- explicit live or paper badge context when known
- visible provisional-versus-confirmed portfolio-state labeling
- clear distinction between symbol-scoped `Held Value` and account-scoped `Account Cash`
- recent runtime event summaries
- active symbol-scoped warnings
- latest order-lifecycle summary
- continued visibility of current sentiment and existing evidence freshness signals

**Acceptance checks**:

- An operator can understand what a bot just did without opening the terminal.
- A stopped symbol with historical evidence is clearly stopped rather than implied to be healthy and current.
- A fresh runtime with no decision row yet still renders coherent runtime truth instead of collapsing into ambiguous `unknown` state.

## Tray Behavior

**Behavior**: Tray remains summary-focused but must stay aligned with the same reconciled runtime truth used by the dashboard.

**Required tray signals**:

- aggregate runtime state counts based on reconciled registry truth
- latest refresh time
- visibility of major failed or exited runtime outcomes

**Acceptance checks**:

- Tray counts do not continue to report dead managed processes as running after reconciliation.
- Tray state remains consistent with the dashboard after start, stop, restart, and unexpected exit scenarios.
