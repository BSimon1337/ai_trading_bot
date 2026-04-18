# Feature Specification: Dashboard and Tray App

**Feature Branch**: `005-dashboard-tray-app`  
**Created**: 2026-04-18  
**Status**: Draft  
**Input**: User description: "I want to work on a new github speckit to make a viewable dashboard whether through the web or desktop. It should also show in the tray when running"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Trading Bot Status (Priority: P1)

As the bot operator, I want a single dashboard I can open locally so I can see whether the trading bot is running, which symbols are active, what mode each symbol is in, and the most recent decisions and fills without reading raw CSV files or terminal logs.

**Why this priority**: The dashboard is the primary operator experience and gives immediate confidence that live, paper, or backtest activity is behaving as expected.

**Independent Test**: Can be tested by running the dashboard against existing decision, fill, and snapshot logs and confirming the operator can identify bot health, active symbols, latest decisions, latest fills, and stale/error states.

**Acceptance Scenarios**:

1. **Given** runtime logs exist for one or more symbols, **When** the operator opens the dashboard, **Then** the dashboard shows each symbol with mode, asset class, status, latest action, latest reason, latest portfolio value or cash values when available, and latest update time.
2. **Given** a symbol has recent decisions and fills, **When** the operator views that symbol, **Then** the dashboard shows the most recent decision rows and fill rows in a readable format.
3. **Given** no log data exists yet, **When** the operator opens the dashboard, **Then** the dashboard shows a clear no-data state instead of crashing or displaying blank tables.

---

### User Story 2 - See Tray Presence While Running (Priority: P2)

As the bot operator, I want a system tray presence while the bot or dashboard monitor is running so I can tell at a glance that monitoring is active and quickly open the dashboard or exit the monitor.

**Why this priority**: The tray indicator solves the current confusion caused by blank or occupied terminal windows and makes the bot feel like an application rather than a loose script.

**Independent Test**: Can be tested by starting the monitor and confirming a tray item appears, displays the current monitor/bot state, opens the dashboard from its menu, and exits cleanly without requiring terminal interaction.

**Acceptance Scenarios**:

1. **Given** the monitor is running, **When** the desktop session has a tray area, **Then** a tray item appears with a clear application label and state indicator.
2. **Given** the tray item is visible, **When** the operator selects "Open Dashboard", **Then** the dashboard opens or is brought to the foreground.
3. **Given** the operator selects "Exit Monitor", **When** the monitor exits, **Then** tray resources are removed and no orphaned monitor process remains.

---

### User Story 3 - Identify Problems Quickly (Priority: P3)

As the bot operator, I want the dashboard and tray state to highlight blocked live runs, stale market data, missing dependencies, disconnected processes, and recent broker/order errors so I can respond before leaving the bot unattended.

**Why this priority**: The bot can be technically running while not trading or while failing safeguards; operator-visible diagnostics reduce financial and operational risk.

**Independent Test**: Can be tested by using fixture logs that represent healthy, stale, blocked-live, failed, and no-data states and confirming the dashboard/tray labels and summaries match each case.

**Acceptance Scenarios**:

1. **Given** the latest log event indicates blocked live execution, **When** the dashboard refreshes, **Then** the affected run is marked blocked with the guardrail reason visible.
2. **Given** the latest decision for a symbol is older than the freshness threshold, **When** the dashboard refreshes, **Then** the symbol is marked stale and the age of the last update is visible.
3. **Given** recent logs include broker rejection or failed runtime events, **When** the operator views the dashboard, **Then** those errors are visible in a dedicated recent issues area.

---

### User Story 4 - Run as a Local App Experience (Priority: P4)

As the bot operator, I want to launch the monitor like a normal local application so I do not have to remember multiple terminal commands to view status.

**Why this priority**: A local app-style launch improves day-to-day usability after the core dashboard and tray behavior are reliable.

**Independent Test**: Can be tested by starting the monitor from a single documented command or shortcut and confirming it starts the dashboard monitor, displays the tray item, and provides clear instructions if required logs or configuration are missing.

**Acceptance Scenarios**:

1. **Given** the project is installed and configured, **When** the operator starts the monitor command or shortcut, **Then** the dashboard monitor starts and the tray item appears within 10 seconds.
2. **Given** required runtime files are missing, **When** the operator starts the monitor, **Then** the app shows a clear setup or no-data state rather than failing silently.

### Edge Cases

- The dashboard must handle missing, empty, partially written, or malformed CSV log files without crashing.
- The dashboard must handle multiple symbols, including stocks and crypto pairs with slash-form symbols.
- The tray feature must degrade gracefully on systems where a tray area is unavailable by keeping the dashboard usable and explaining tray unavailability.
- The monitor must not display stale information as healthy; stale timestamps must be visually distinct.
- The monitor must not expose raw credential values.
- Safe controls must not bypass existing live trading safeguards, confirmations, or kill-switch behavior.
- Closing a dashboard view must not accidentally stop a running trading bot unless the operator explicitly selects an exit or stop action.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a local dashboard that summarizes configured bot instances, symbols, asset classes, runtime modes, health states, latest decisions, latest fills, and latest update times.
- **FR-002**: System MUST show recent decision and fill history in a readable operator-facing view with enough detail to understand action, reason, source, quantity, cash/portfolio context, and result.
- **FR-003**: System MUST identify and visually distinguish healthy, running, paper, live, blocked, stale, failed, and no-data states.
- **FR-004**: System MUST provide a system tray presence while the monitor is running on supported desktop environments.
- **FR-005**: The tray presence MUST provide at minimum Open Dashboard, status summary, and Exit Monitor actions.
- **FR-006**: System MUST support local viewing through a browser and MAY additionally provide a desktop-window wrapper, provided both expose the same underlying monitoring information.
- **FR-007**: System MUST refresh displayed status automatically often enough for an operator to notice live changes without manual page reloads.
- **FR-008**: System MUST read from the existing runtime evidence sources for decisions, fills, daily snapshots, and run events rather than requiring duplicate manual data entry.
- **FR-009**: System MUST handle missing, empty, malformed, or partially written runtime evidence files gracefully and show operator-readable messages.
- **FR-010**: System MUST support multiple configured bot instances and symbols, including stocks and crypto assets.
- **FR-011**: System MUST avoid showing credential values, secret tokens, or other sensitive environment values in the dashboard, tray text, or logs.
- **FR-012**: System MUST provide operator-visible diagnostics for recent failures, blocked live attempts, stale market data, dependency warnings, and broker/order rejections when that information is available from runtime evidence.
- **FR-013**: System MUST preserve existing fail-closed live trading behavior; any dashboard or tray control that affects runtime state must respect existing safeguards and explicit live confirmations.
- **FR-014**: System MUST document how to start, view, and stop the monitor and how to distinguish monitoring windows from bot process windows.
- **FR-015**: System MUST support a read-only monitoring mode that cannot place, approve, or cancel trades.

### Key Entities *(include if feature involves data)*

- **Dashboard Instance**: Represents one monitored bot context, including label, symbols, log paths, current status, latest decision, latest fill, and latest snapshot.
- **Runtime Status**: Represents the operator-facing health state of a bot instance or symbol, including running, live, paper, blocked, stale, failed, and no-data.
- **Decision Summary**: Represents a parsed trade decision with timestamp, symbol, action, reason, source, sentiment/model evidence, quantity, cash/portfolio context, and result.
- **Fill Summary**: Represents a parsed order/fill record with timestamp, symbol, side, quantity, order identifier, notional value, and result.
- **Tray State**: Represents the desktop indicator state, including label, status color/text, last update time, and available menu actions.
- **Monitor Configuration**: Represents operator settings for dashboard port, monitored symbols/instances, refresh interval, tray enablement, and read-only mode.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: Existing local monitoring flow in `monitor_app.py`, dashboard template in `templates/monitor.html`, runtime log contracts in `tradingbot/execution/logging.py`, configuration parsing in `tradingbot/config/settings.py`, preflight/readiness concepts in `tradingbot/app/preflight.py`, and existing decision/fill/snapshot CSV outputs.
- **Planned deviations**: The current dashboard is browser-only and log-file oriented. This feature may add a tray-backed monitor launcher and, if justified during planning, a desktop-window wrapper around the same local dashboard experience. The dashboard must remain usable from a browser even if desktop tray support is unavailable.
- **New dependencies**: Any added dependency must be pinned to an exact version, must have been published at least 7 days before adoption, and must be justified during planning. Desktop/tray dependencies are optional unless selected in the implementation plan.
- **Operational impact**: Adds an operator-facing monitor/tray runtime, new launch documentation, possible monitor-specific logs, possible monitor-specific environment variables, and clearer visibility into existing paper/live behavior. It must not weaken live safeguards or expose credentials.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can start the monitor and open the dashboard from a documented command or tray action in under 60 seconds.
- **SC-002**: Dashboard status for at least 10 monitored symbols or instances renders within 3 seconds using existing local runtime evidence.
- **SC-003**: The dashboard correctly classifies healthy, stale, blocked, failed, and no-data fixture states in 100% of acceptance tests.
- **SC-004**: The tray item appears within 10 seconds on supported desktop environments and provides Open Dashboard and Exit Monitor actions.
- **SC-005**: Missing or malformed runtime evidence files produce a readable no-data or warning state in 100% of tests instead of crashing.
- **SC-006**: No credential values appear in dashboard output, tray labels, or monitor logs during validation.
- **SC-007**: A user can identify the latest action, latest reason, and latest update time for each monitored symbol within 15 seconds of opening the dashboard.

## Assumptions

- The first version is intended for a local operator running the bot on their own computer, not a public multi-user hosted service.
- Browser-based viewing is required; a desktop window is optional as long as the tray item can open the dashboard.
- The tray feature targets desktop environments that support system tray or notification-area icons and will degrade gracefully elsewhere.
- The monitor is read-only by default. Any future controls that stop or start bot processes must be explicitly designed to preserve existing safeguards.
- Existing CSV runtime evidence remains the source of truth for dashboard status unless a later plan introduces a safer runtime status channel.
- Live trading status visibility is in scope; changing live trading permissions or approving trades from the dashboard is out of scope for this feature.
- If new packages are introduced, each selected version will be pinned exactly and verified as published at least 7 days earlier.
