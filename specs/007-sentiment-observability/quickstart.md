# Quickstart: Sentiment Observability

## Goal

Validate that the local monitor explains current sentiment state per bot using existing FinBERT/news evidence, including fallback behavior and bounded headline previews.

## Prerequisites

- Python 3.10 virtual environment is available.
- Existing project dependencies are installed.
- The monitor feature is already launchable locally.
- Local runtime evidence exists for decision logs, or fixture scenarios can be generated for sentiment/fallback validation.

## Start the Monitor

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m tradingbot.app.tray --no-tray --host 127.0.0.1 --port 8080
```

Open:

```text
http://127.0.0.1:8080
```

## Validate Current Sentiment Visibility

Use recent runtime evidence where at least one symbol has current sentiment data.

Expected result:

- Each monitored symbol shows its latest sentiment label and probability when available.
- The dashboard shows the sentiment source for each symbol.
- The sentiment timestamp is readable and bounded to the latest trusted state.

## Validate Fallback Transparency

Use runtime evidence or a dependency-disabled scenario where the bot falls back to neutral sentiment.

Expected result:

- The dashboard clearly shows that the sentiment state is fallback-driven.
- Fallback-neutral state is distinguishable from normal model-scored neutral sentiment.
- The monitor remains readable and does not escalate fallback into a false critical failure.

## Validate Headline Evidence Preview

Use news evidence with several recent headlines for at least one symbol.

Expected result:

- The dashboard shows headline count.
- The dashboard shows a bounded preview of recent headlines.
- The preview stays readable and does not overwhelm the monitor layout.

## Validate Sentiment Trend

Use evidence where recent sentiment observations differ over time.

Expected result:

- The dashboard shows a short recent sentiment trend or history.
- Operators can tell whether sentiment has been stable, changing, or unavailable without opening raw files.

## Validate Stale And No-Headline Sentiment

Use evidence where one symbol has a current decision row but an older `sentiment_observed_at`, and another symbol has `headline_count=0`.

Expected result:

- The stale symbol is explicitly marked as stale rather than fresh.
- The no-headline symbol explains that no recent headlines were available.
- Fallback or no-headline messaging remains informational and does not become a false critical runtime issue.

## Automated Validation

Run:

```powershell
cd C:\Users\Beau\ai_trading_bot
.\.venv\Scripts\python.exe -m pytest tests/unit/test_monitor_data.py tests/contract/test_dashboard_monitor_contract.py tests/smoke/test_monitor_entrypoint.py
```

Expected result:

- Tests pass.
- Current sentiment visibility, fallback-state handling, bounded headline previews, and dashboard rendering are covered.
- Stale sentiment and no-headline sentiment rendering are covered.

## Safety Check

Expected result:

- The monitor remains read-only.
- No order placement, order cancellation, or live-approval behavior is introduced by this feature.

## Manual Validation Notes

- Confirm a stale sentiment row still shows the latest runtime status correctly while labeling the sentiment context as stale.
- Confirm a fallback-neutral or no-headline symbol still renders a readable sentiment explanation instead of empty cells.
- Confirm the tray remains view-only: open dashboard, refresh status, and exit monitor are still the only tray actions.
- Record whether the dashboard shows current sentiment, headline previews, and trend history for each actively monitored symbol after a live refresh.
