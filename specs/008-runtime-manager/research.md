# Research: Runtime Manager

## Decision 1: Use standard-library subprocess management with one child process per symbol

**Decision**: Manage each bot runtime as its own child process using Python standard-library process primitives rather than adding an external supervisor dependency.

**Rationale**: The current bot already runs one symbol per live process because Lumibot live mode does not support multiple live strategies in one process. A standard-library approach keeps the runtime layer lightweight, locally debuggable, and aligned with the existing Python-first structure.

**Alternatives considered**:

- **External process manager dependency**: Rejected for the first version because it adds operational complexity and new dependencies before the local app-owned lifecycle model is proven.
- **Single multi-symbol runtime process**: Rejected because it conflicts with the current Lumibot live limitation and would force larger strategy/runtime changes.

## Decision 2: Persist runtime state in a local JSON registry owned by the app

**Decision**: Store managed runtime/session state in a local JSON registry file that the monitor can read independently of the launcher process.

**Rationale**: The monitor is already file-driven and loosely coupled. A JSON registry keeps the runtime-manager state durable, inspectable, and easy to merge into the current dashboard/tray refresh cycle without requiring an always-shared in-memory service.

**Alternatives considered**:

- **In-memory only runtime state**: Rejected because the monitor would lose state when processes restart or when the launcher and monitor are not tightly coupled.
- **Database-backed runtime state**: Rejected because it adds unnecessary infrastructure for a single-machine local application.

## Decision 3: Keep runtime-manager controls behind existing live-safety expectations

**Decision**: Runtime-manager start and restart actions will honor the current live-trading safety model rather than inventing a separate approval path.

**Rationale**: Start and restart actions are operationally sensitive in live mode. Reusing the current explicit live enablement and confirmation expectations preserves the project’s fail-closed behavior and avoids silent live activation through a new control surface.

**Alternatives considered**:

- **Ungated runtime-manager launch path**: Rejected because it would create a backdoor around current live safeguards.
- **Separate runtime-manager-only approval model**: Rejected because it would duplicate safety logic and increase the chance of inconsistent behavior.

**Implementation note**: The managed launch environment only carries symbol-scoped runtime values such as `SYMBOLS`, `DECISION_LOG_PATH`, `FILL_LOG_PATH`, `DAILY_SNAPSHOT_PATH`, and `RUNTIME_REGISTRY_PATH`. The runtime registry itself does not persist Alpaca credentials or confirmation tokens.

## Decision 4: Show runtime-manager state in the existing monitor instead of building a new control UI first

**Decision**: Add runtime lifecycle state to the current monitor and tray surfaces before introducing richer interactive controls.

**Rationale**: The operator already uses the monitor as the main source of truth. Making runtime lifecycle visible there first improves trust and debugging immediately while laying the groundwork for later interactive start/stop controls.

**Alternatives considered**:

- **Build controls first, visibility second**: Rejected because hidden runtime behavior would make the new control plane harder to trust.
- **Separate runtime console UI**: Rejected because it would fragment the operator experience.

**Implementation note**: Runtime-manager state now takes precedence over stale CSV evidence for `stopped`, `paused`, `failed`, and fresh restart cases so the operator-facing monitor reflects current app-owned lifecycle truth rather than old trading artifacts.
