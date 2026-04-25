# Research: Dashboard and Tray App

## Decision: Reuse the Existing Browser Dashboard as the Primary UI

**Decision**: Keep the existing local browser dashboard as the required viewing surface and improve it rather than replacing it with a separate desktop UI.

**Rationale**: The repository already has `monitor_app.py`, `templates/monitor.html`, CSV-backed status parsing, and Flask in the pinned runtime stack. Reusing that flow satisfies the constitution's existing-project consistency rule and reduces the risk of introducing a large desktop framework before the monitoring model is stable.

**Alternatives considered**:

- **Full desktop application first**: Rejected for this feature because it adds a larger runtime boundary and packaging complexity before the dashboard/tray requirements are proven.
- **Separate JavaScript frontend**: Rejected for now because the current template-based dashboard is sufficient and avoids npm dependency/version governance work.
- **Terminal-only monitor**: Rejected because the user explicitly wants a viewable dashboard and tray presence.

## Decision: Add Tray Presence with `pystray==0.19.5` and `Pillow==11.3.0`

**Decision**: Use `pystray==0.19.5` for cross-platform tray icon/menu support and `Pillow==11.3.0` for icon image creation/loading.

**Rationale**: `pystray` is a small Python tray library that fits the existing Python-first architecture. PyPI lists `pystray==0.19.5` with an upload date of 2023-09-17, which is well older than the project's 7-day dependency age requirement. Pillow provides the image support expected by pystray; Pillow `11.3.0` was released on 2025-07-01, also older than 7 days as of 2026-04-25.

**Alternatives considered**:

- **No tray dependency**: Rejected because native tray behavior is a core requirement and cannot be implemented reliably with standard library modules alone.
- **Desktop framework with built-in tray**: Rejected for this phase because it would force a heavier app stack when the only required desktop-native feature is tray presence.
- **OS-specific tray code**: Rejected because it would be harder to test and maintain than one pinned Python dependency.

## Decision: Read-Only Monitor by Default

**Decision**: The dashboard/tray monitor will be read-only in this feature. It may open the dashboard and exit the monitor process, but it will not place, approve, cancel, start, or stop trades.

**Rationale**: This preserves fail-closed live trading behavior and avoids creating a second control plane for trading decisions. The current user need is visibility and app-like presence, not trade approval.

**Alternatives considered**:

- **Start/stop bot controls in tray**: Deferred because process supervision and safe stop semantics need a separate design to avoid killing live trading unexpectedly.
- **Trade controls in dashboard**: Rejected for this feature because they would materially change trading safety scope.

## Decision: CSV Evidence Remains the Source of Truth

**Decision**: Continue reading existing decision, fill, snapshot, and run-event CSV evidence for dashboard status.

**Rationale**: The current bot already writes durable operator evidence. Building the monitor from those contracts keeps the feature useful for backtest, paper, and live modes without requiring a new status server or database.

**Alternatives considered**:

- **In-memory bot status API**: Rejected for this phase because it would only work while a bot process is reachable and would not cover historical evidence.
- **Database-backed monitor state**: Rejected because current scale is a single local operator and CSV evidence is sufficient.

## Decision: Browser Dashboard Required, Desktop Window Optional

**Decision**: The plan will require a browser-viewable dashboard and tray item. A desktop-window wrapper may be added later only if it reuses the same dashboard data and does not complicate installation.

**Rationale**: This meets "web or desktop" by preserving web access and adding desktop tray presence. It keeps v1 small and testable while leaving a path to a desktop wrapper.

**Alternatives considered**:

- **Desktop-only app**: Rejected because browser viewing is already working and useful across environments.
- **Both full web and full desktop immediately**: Rejected as unnecessary scope expansion for the first dashboard/tray feature.

## Decision: Fixture-Driven Validation

**Decision**: Use local fixture CSV files to validate healthy, no-data, stale, blocked-live, failed, malformed-log, and broker-error states.

**Rationale**: Monitoring correctness is mostly data interpretation. Fixture-driven tests make these states repeatable without needing live trading or Alpaca network calls.

**Alternatives considered**:

- **Manual-only validation**: Rejected because dashboard status logic is easy to regress.
- **Live trading validation**: Rejected as unnecessary and too risky for a monitor-only feature.
