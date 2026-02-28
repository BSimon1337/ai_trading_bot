# Methodology Notes

- Evaluation window: 2024-01-01 to 2024-12-31
- Symbols: SPY, BTCUSD
- Model used: `models\xgb_full.joblib`
- Signals are generated from model probability (`prob_up`) with configuration-specific thresholds.
- Strategy return per row = `signal * forward_return * risk_fraction`.
- Config matrix compares conservative/medium/aggressive risk and threshold settings.
- Benchmark is buy-and-hold using each symbol's `forward_return`.
