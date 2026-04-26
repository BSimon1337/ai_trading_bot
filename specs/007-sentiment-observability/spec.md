# Feature Specification: Sentiment Observability

**Feature Branch**: `007-sentiment-observability`  
**Created**: 2026-04-25  
**Status**: Draft  
**Input**: User description: "Focus on the sentiment analysis next and expose more FinBERT and news-sentiment information in the dashboard so the monitoring experience is more explainable and useful."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See Current Sentiment State Per Bot (Priority: P1)

As the bot operator, I want each monitored symbol to show its current sentiment state so I can immediately tell whether recent news is being interpreted as positive, negative, neutral, or fallback-driven without opening logs or reading code.

**Why this priority**: The dashboard already explains runtime health and trades, but it does not yet explain the NLP input that influences decisions. That missing visibility makes the system harder to trust and harder to present clearly.

**Independent Test**: Can be tested by loading monitor evidence from symbols with recent sentiment activity and confirming the dashboard shows the latest sentiment label, confidence, source, and freshness for each symbol without breaking existing monitor behavior.

**Acceptance Scenarios**:

1. **Given** a symbol has recent FinBERT-scored news, **When** the operator opens the dashboard, **Then** the symbol card shows the latest sentiment label, confidence, and source for that symbol.
2. **Given** a symbol is using a neutral fallback because FinBERT or news input is unavailable, **When** the operator views the dashboard, **Then** the monitor clearly shows that the sentiment state is fallback-driven rather than a real positive or negative signal.
3. **Given** multiple live or paper symbol processes are being monitored, **When** the operator views the dashboard, **Then** each symbol shows its own current sentiment state rather than a single shared summary.

---

### User Story 2 - Understand the News Behind Sentiment (Priority: P2)

As the bot operator, I want to see the recent headlines and sentiment evidence behind each symbol so I can explain why the monitor shows a particular sentiment state and debug cases where the bot keeps holding or trading unexpectedly.

**Why this priority**: A label alone is helpful, but the dashboard becomes much more valuable when it can explain the news context that produced the label.

**Independent Test**: Can be tested by loading symbols with recent headline evidence and confirming the dashboard shows headline count, representative recent headlines, and recent sentiment trend information without requiring access to raw CSV files.

**Acceptance Scenarios**:

1. **Given** a symbol has recent news headlines, **When** the operator opens that symbol’s dashboard detail view, **Then** the monitor shows the number of headlines analyzed and a bounded list of recent headline samples.
2. **Given** recent sentiment states have changed across monitor refreshes, **When** the operator views the sentiment detail, **Then** the dashboard shows a readable recent sentiment trend rather than only the single latest label.
3. **Given** no recent headlines were available, **When** the operator checks the sentiment section, **Then** the dashboard makes the absence of headline evidence explicit instead of leaving the operator to guess.

---

### User Story 3 - Keep Sentiment Visibility Safe and Explainable (Priority: P3)

As the bot operator, I want sentiment details to remain bounded, readable, and safe so the monitor stays useful during live trading and still explains fallback conditions without flooding the screen or exposing sensitive information.

**Why this priority**: Sentiment visibility should improve trust, not create a wall of text or a confusing mix of current and stale context.

**Independent Test**: Can be tested by mixing current sentiment evidence, stale sentiment evidence, and fallback conditions, then confirming the monitor keeps the latest sentiment context readable and bounded while preserving safe read-only behavior.

**Acceptance Scenarios**:

1. **Given** a symbol has many recent headlines, **When** the operator opens the dashboard, **Then** the monitor shows only a bounded preview rather than dumping an unbounded headline list.
2. **Given** the latest sentiment evidence is stale relative to current bot activity, **When** the operator views the dashboard, **Then** the monitor indicates that the sentiment context is older rather than presenting it as fresh.
3. **Given** the monitor refreshes during live trading, **When** the operator views sentiment details, **Then** no control or order-flow behavior is added and the monitor remains read-only.

### Edge Cases

- A symbol can have current runtime activity but no recent headlines, and the dashboard still needs to explain the fallback or no-news state clearly.
- FinBERT can be unavailable locally because model dependencies failed to load, and the monitor must distinguish that from a neutral market interpretation.
- Headline evidence can exist for one symbol but not another in the same refresh cycle.
- Recent headline text can be long or repetitive, so the monitor must keep it bounded and readable.
- Sentiment evidence can lag slightly behind trading iterations, and the dashboard must not imply that older sentiment is freshly evaluated.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST show the latest sentiment label for each monitored symbol when current sentiment evidence exists.
- **FR-002**: System MUST show the latest sentiment confidence or probability value for each monitored symbol when that evidence exists.
- **FR-003**: System MUST show whether the displayed sentiment came from external news, local fixture news, or a neutral fallback path.
- **FR-004**: System MUST distinguish real neutral sentiment from fallback-driven neutral sentiment in the monitor.
- **FR-005**: System MUST show the number of recent headlines analyzed for each monitored symbol when headline evidence exists.
- **FR-006**: System MUST show a bounded preview of recent headlines associated with the latest sentiment context for each monitored symbol.
- **FR-007**: System MUST show a readable recent sentiment trend or history for each monitored symbol when multiple recent sentiment observations exist.
- **FR-008**: System MUST indicate when the latest sentiment evidence is stale or unavailable instead of presenting it as fresh.
- **FR-009**: System MUST preserve read-only monitor behavior and MUST NOT introduce trading controls, broker calls for execution, or live approval behavior.
- **FR-010**: System MUST reuse the existing sentiment, news, monitor, and dashboard patterns already present in the repository unless a documented deviation is required.
- **FR-011**: System MUST handle missing, partial, or fallback-only sentiment evidence gracefully without crashing the monitor.

### Key Entities *(include if feature involves data)*

- **Sentiment Snapshot**: The latest trusted per-symbol sentiment view, including label, confidence, source, fallback state, and freshness.
- **Headline Evidence Preview**: A bounded set of recent headline samples and counts associated with the displayed sentiment context.
- **Sentiment Trend Entry**: A recent sentiment observation for a symbol that allows the monitor to show short-term direction or consistency.
- **Sentiment Availability State**: The operator-facing explanation of whether sentiment came from FinBERT-scored news, local fixtures, no headlines, or neutral fallback behavior.

## Existing System Alignment *(mandatory)*

- **Existing components reused**: `tradingbot/sentiment/scoring.py`, `tradingbot/data/news.py`, `tradingbot/strategy/lumibot_strategy.py`, `tradingbot/app/monitor.py`, `tradingbot/app/tray.py`, `templates/monitor.html`, and the existing CSV-backed monitor evidence patterns.
- **Planned deviations**: None expected. This feature extends observability and explanation inside the current local monitor rather than changing the runtime architecture.
- **New dependencies**: None expected.
- **Operational impact**: The dashboard will expose clearer sentiment visibility per symbol, including FinBERT/fallback context, headline evidence, and recent sentiment history, while remaining read-only and local-evidence-driven.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can identify the current sentiment label, confidence, and source for any monitored symbol within 10 seconds of opening its dashboard card or detail view.
- **SC-002**: In validation scenarios with fallback-only sentiment, 100% of affected symbols clearly indicate fallback state instead of appearing indistinguishable from normal neutral sentiment.
- **SC-003**: In validation scenarios with recent headline evidence, 100% of monitored symbols show bounded headline previews and headline counts without overflowing the dashboard layout.
- **SC-004**: In validation scenarios with multiple recent sentiment observations, operators can determine the recent sentiment trend for a symbol without reading raw log files.
- **SC-005**: The monitor continues to refresh and render without crashing in 100% of tests that include missing, stale, or partial sentiment evidence.

## Assumptions

- FinBERT-based sentiment scoring remains the primary local NLP interpretation path for financial headlines in this project.
- News evidence already available through the current runtime or offline fixture flows will remain the source of truth for sentiment observability.
- This feature improves visibility of sentiment behavior but does not change the strategy’s underlying trade decision rules.
- Headline previews can be bounded for readability and do not need to show every historical headline in the monitor.
- Runtime manager and interactive control features remain out of scope for this sentiment observability feature.
