# Research: Interactive Bot Controls

## Decision 1: Reuse the existing Flask monitor with server-handled action posts

**Decision**: Implement interactive controls through the current Flask monitor using server-handled action submissions rather than adding a separate frontend stack or standalone control service.

**Rationale**: The current monitor already owns the operator-facing runtime view, and the runtime manager already provides the lifecycle behavior. Extending that existing monitor path keeps the feature aligned with the repo's Python-first, template-based architecture and avoids unnecessary UI or tooling expansion.

**Runtime-manager reuse points**:

- `tradingbot/app/runtime_manager.py` remains the sole executor for start, stop, and restart actions.
- `tradingbot/app/monitor.py` becomes the request and response layer for operator-issued lifecycle actions.
- `templates/monitor.html` becomes the primary local action surface, while existing terminal commands remain fallback tools.
- `tradingbot/app/tray.py` continues to reflect state and outcomes without becoming the main control entrypoint.

**Alternatives considered**:

- **New frontend framework**: Rejected because it adds a second UI architecture and unnecessary build complexity for a small local operator app.
- **CLI-only control with monitor visibility only**: Rejected because the runtime-manager backend is already proven and the main remaining gap is in-dashboard usability.

## Decision 2: Extend the runtime registry with bounded recent control activity

**Decision**: Store recent dashboard-issued control actions alongside runtime registry state using a bounded recent-action history.

**Rationale**: The runtime registry is already the app-owned source of truth for current managed lifecycle state. Extending it with recent control activity keeps control evidence durable, inspectable, and available even when there is no fresh trading evidence for a symbol.

**Interactive-control touchpoints**:

- Per-symbol control availability is derived from the same managed runtime state that already powers dashboard runtime visibility.
- Recent control history must remain visible even when trading CSVs are quiet, especially for stopped stock symbols and paused crypto symbols.
- Registry-backed control evidence lets us preserve one operator story across dashboard refreshes instead of relying on transient UI notifications.

**Alternatives considered**:

- **In-memory only flash messages**: Rejected because action history would disappear on refresh and would not help with operator trust or debugging.
- **Separate audit database or new file family**: Rejected because the app is still a single-machine local tool and a second persistence path would add complexity without clear value.

## Decision 3: Use explicit live confirmation in the dashboard before live start or restart

**Decision**: Dashboard-issued live start and restart actions will require an explicit confirmation step and backend safeguard validation before the runtime manager is called.

**Rationale**: Interactive control is a high-leverage capability. Requiring a clear live-specific confirmation keeps the UI aligned with the app's fail-closed safety posture and prevents the dashboard from becoming a silent live activation path.

**Operator-safe wording expectations**:

- Paper and live actions should be labeled before the operator clicks, not only after submission.
- Any blocked action should explain whether the block came from runtime state, live safeguards, or confirmation requirements.
- The same wording principles should hold for stock and crypto controls so asset class does not change the safety model unexpectedly.

**Alternatives considered**:

- **Single-click live controls**: Rejected because they make accidental live changes too easy.
- **No distinction between paper and live control wording**: Rejected because it increases operator confusion at the exact moment decisions matter most.

## Decision 4: Use one shared control pipeline for stock and crypto symbols

**Decision**: Drive dashboard controls through the same runtime-manager action path for both stock and crypto symbols, using existing asset-class parsing only to shape labels, availability, and status messaging where needed.

**Rationale**: The user explicitly wants stock trading capability preserved, and the runtime-manager layer is already symbol-scoped rather than crypto-specific. One shared control path avoids bifurcated logic and reduces the chance that stock support quietly regresses while crypto continues to evolve.

**Coverage expectation**:

- Stock support is part of the initial acceptance path for this feature, not a later enhancement.
- Mixed symbol sets must remain understandable in one dashboard view, even if only one asset class is actively trading at a given moment.

**Alternatives considered**:

- **Crypto-first control surface with later stock retrofit**: Rejected because it would almost guarantee stock support becomes a second-class path.
- **Separate stock and crypto control implementations**: Rejected because lifecycle actions are the same even if trading behavior differs later.
