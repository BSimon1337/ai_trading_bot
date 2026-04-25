# Monitor Fixtures

This directory holds CSV fixture builders and sample runtime evidence for the
dashboard and tray monitor features.

Core fixture states already covered or expected by the monitor test suite:

- healthy running
- paper
- active live
- blocked live
- stale data
- malformed CSV
- no data
- broker rejection

Refinement scenarios for `006-monitor-accuracy-refinement`:

- healthy restart after an older failed or blocked run
- multiple symbol-specific instances sharing one account snapshot context
- current position with no recent fill in the active evidence window
- mixed current and archived evidence where only the active window should drive status
- informational note scenarios such as slight negative day PnL without operational failure
- malformed historical evidence that remains readable for debugging but does not dominate the active monitor view

Fixture guidance:

- Keep active evidence and historical evidence easy to distinguish by timestamp.
- Prefer slash-form crypto symbols such as `BTC/USD` and `ETH/USD` in mixed-instance scenarios.
- Include at least one scenario where fill-derived value is unavailable so held-value fallback behavior can be validated.
- Include one scenario where a bot is healthy, idle, and producing current decisions so tests can distinguish "holding" from "stalled."
