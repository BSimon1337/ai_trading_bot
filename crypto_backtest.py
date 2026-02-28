from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from utils import setup_logging

TECH_FEATURES = ["ret_1", "sma_20", "ema_20", "rsi_14", "volume_z20"]
SENTIMENT_FEATURES = ["sentiment_mean", "sentiment_count"]
FEATURES = TECH_FEATURES + SENTIMENT_FEATURES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast crypto backtest from local dataset + trained model.")
    parser.add_argument("--symbol", default="BTCUSD", choices=["BTCUSD", "ETHUSD"], help="Crypto symbol.")
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to symbol dataset CSV. Defaults to data/model_dataset/{symbol}_dataset.csv",
    )
    parser.add_argument("--model-path", default="models/xgb_full.joblib", help="Trained model artifact path.")
    parser.add_argument("--start", default=None, help="Optional start date (YYYY-MM-DD).")
    parser.add_argument("--end", default=None, help="Optional end date (YYYY-MM-DD).")
    parser.add_argument(
        "--long-threshold",
        type=float,
        default=0.55,
        help="Probability threshold for long signal.",
    )
    parser.add_argument(
        "--allow-short",
        action="store_true",
        help="Enable short signals when prob <= 1 - long-threshold.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional output path for per-row backtest results.",
    )
    return parser.parse_args()


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def _sharpe(returns: pd.Series, periods_per_year: int = 365) -> float:
    if returns.empty:
        return 0.0
    std = returns.std(ddof=0)
    if std == 0 or np.isnan(std):
        return 0.0
    return float(np.sqrt(periods_per_year) * (returns.mean() / std))


def _load_dataset(path: Path, symbol: str, start: str | None, end: str | None) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Dataset is empty: {path}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df = df[df["symbol"] == symbol].copy()
    if start:
        start_ts = pd.to_datetime(start, utc=True)
        df = df[df["timestamp"] >= start_ts]
    if end:
        end_ts = pd.to_datetime(end, utc=True)
        df = df[df["timestamp"] <= end_ts]
    df["forward_return"] = pd.to_numeric(df["forward_return"], errors="coerce")
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["forward_return"]).sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise ValueError("No rows after filtering; check symbol/date range.")
    return df


def main() -> None:
    setup_logging()
    args = parse_args()
    dataset_path = Path(args.dataset) if args.dataset else Path(f"data/model_dataset/{args.symbol}_dataset.csv")
    model_path = Path(args.model_path)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    df = _load_dataset(dataset_path, args.symbol, args.start, args.end)
    model = joblib.load(model_path)

    proba = (
        model.predict_proba(df[["symbol"] + FEATURES])[:, 1]
        if hasattr(model, "predict_proba")
        else model.predict(df[["symbol"] + FEATURES]).astype(float)
    )
    df["prob_up"] = proba

    short_threshold = 1.0 - float(args.long_threshold)
    signal = np.where(df["prob_up"] >= args.long_threshold, 1, 0)
    if args.allow_short:
        signal = np.where(df["prob_up"] <= short_threshold, -1, signal)
    df["signal"] = signal
    df["strategy_return"] = df["signal"] * df["forward_return"]
    df["benchmark_return"] = df["forward_return"]
    df["strategy_equity"] = (1.0 + df["strategy_return"]).cumprod()
    df["benchmark_equity"] = (1.0 + df["benchmark_return"]).cumprod()

    start_value = 100000.0
    end_value = start_value * float(df["strategy_equity"].iloc[-1])
    benchmark_end = start_value * float(df["benchmark_equity"].iloc[-1])
    strategy_total_return = float(df["strategy_equity"].iloc[-1] - 1.0)
    benchmark_total_return = float(df["benchmark_equity"].iloc[-1] - 1.0)
    max_dd = _max_drawdown(df["strategy_return"])
    sharpe = _sharpe(df["strategy_return"])
    trade_events = int((pd.Series(df["signal"]).diff().abs().fillna(0) > 0).sum())

    if args.output_csv:
        output_path = Path(args.output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"Saved detailed backtest rows: {output_path}")

    print("\n=== Crypto Backtest Summary ===")
    print(f"Symbol: {args.symbol}")
    print(f"Rows: {len(df)}")
    print(f"Window: {df['timestamp'].iloc[0].date()} -> {df['timestamp'].iloc[-1].date()}")
    print(f"Model: {model_path}")
    print(f"Start Value: ${start_value:,.2f}")
    print(f"End Value:   ${end_value:,.2f}")
    print(f"Benchmark End Value: ${benchmark_end:,.2f}")
    print(f"Strategy Total Return: {strategy_total_return * 100.0:.2f}%")
    print(f"Benchmark Total Return: {benchmark_total_return * 100.0:.2f}%")
    print(f"Sharpe: {sharpe:.2f}")
    print(f"Max Drawdown: {max_dd * 100.0:.2f}%")
    print(f"Trade Events: {trade_events}")
    print("================================\n")


if __name__ == "__main__":
    main()
