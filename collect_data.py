from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from config import load_config
from data_handler import DataHandler
from utils import setup_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and build sentiment + price dataset.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["SPY", "BTCUSD", "ETHUSD"],
        help="Symbols to collect (example: SPY BTCUSD ETHUSD).",
    )
    parser.add_argument(
        "--timeframe",
        default="1Day",
        help="Alpaca bar timeframe (for example: 1Day, 1Hour, 15Min).",
    )
    parser.add_argument("--start", default=None, help="Start date YYYY-MM-DD.")
    parser.add_argument("--end", default=None, help="End date YYYY-MM-DD.")
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for raw and processed datasets.",
    )
    parser.add_argument(
        "--forward-bars",
        type=int,
        default=1,
        help="Label horizon in bars (1 = next bar return).",
    )
    return parser.parse_args()


def _normalize_news_symbol(symbol: str) -> str:
    clean = symbol.replace("/", "").upper()
    if clean.endswith("USD") and len(clean) > 3:
        return clean[:-3]
    return clean


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, 1e-12)
    return 100.0 - (100.0 / (1.0 + rs))


def _prepare_bars_features(bars: pd.DataFrame) -> pd.DataFrame:
    if bars.empty:
        return bars
    bars = bars.copy()
    bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True, errors="coerce")
    bars = bars.dropna(subset=["timestamp"]).sort_values("timestamp")

    bars["ret_1"] = bars["close"].pct_change()
    bars["sma_20"] = bars["close"].rolling(20).mean()
    bars["ema_20"] = bars["close"].ewm(span=20, adjust=False).mean()
    bars["rsi_14"] = _compute_rsi(bars["close"], period=14)

    vol_mean = bars["volume"].rolling(20).mean()
    vol_std = bars["volume"].rolling(20).std()
    bars["volume_z20"] = (bars["volume"] - vol_mean) / vol_std.replace(0.0, 1e-12)
    return bars


def _build_sentiment_daily(news_df: pd.DataFrame) -> pd.DataFrame:
    if news_df.empty:
        return pd.DataFrame(columns=["date", "sentiment_mean", "sentiment_count"])

    news_df = news_df.copy()
    news_df["headline"] = news_df["headline"].fillna("")
    from finbert_utils import score_headlines

    news_df["sentiment_score"] = score_headlines(news_df["headline"].tolist())
    news_df["timestamp"] = pd.to_datetime(news_df["created_at"], utc=True, errors="coerce")
    news_df = news_df.dropna(subset=["timestamp"])
    news_df["date"] = news_df["timestamp"].dt.date

    grouped = (
        news_df.groupby("date", as_index=False)
        .agg(sentiment_mean=("sentiment_score", "mean"), sentiment_count=("sentiment_score", "size"))
        .sort_values("date")
    )
    return grouped


def _label_dataset(df: pd.DataFrame, forward_bars: int) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy().sort_values("timestamp")
    df["forward_return"] = df["close"].shift(-forward_bars) / df["close"] - 1.0
    df["target_up"] = (df["forward_return"] > 0).astype("int64")
    return df


def _ensure_dirs(base: Path) -> Dict[str, Path]:
    raw_news = base / "raw_news"
    raw_bars = base / "raw_bars"
    model_data = base / "model_dataset"
    raw_news.mkdir(parents=True, exist_ok=True)
    raw_bars.mkdir(parents=True, exist_ok=True)
    model_data.mkdir(parents=True, exist_ok=True)
    return {"raw_news": raw_news, "raw_bars": raw_bars, "model_dataset": model_data}


def _safe_symbol_filename(symbol: str) -> str:
    return symbol.replace("/", "_")


def main() -> None:
    setup_logging()
    args = parse_args()
    cfg = load_config()
    data_handler = DataHandler(
        source="alpaca",
        api_key=cfg.api_key,
        api_secret=cfg.api_secret,
        base_url=cfg.base_url,
    )

    start = args.start or cfg.start_date.strftime("%Y-%m-%d")
    end = args.end or cfg.end_date.strftime("%Y-%m-%d")
    out_dirs = _ensure_dirs(Path(args.output_dir))

    summary: List[dict] = []
    all_rows: List[pd.DataFrame] = []

    for symbol in args.symbols:
        bars_df = data_handler.get_bars(
            symbol=symbol,
            timeframe=args.timeframe,
            start=start,
            end=end,
            adjustment="raw",
        )
        bars_df = _prepare_bars_features(bars_df)

        news_symbol = _normalize_news_symbol(symbol)
        news_records = data_handler.get_news_records(
            symbol=news_symbol,
            start=start,
            end=end,
            limit=200,
            max_pages=200,
        )
        news_df = pd.DataFrame(news_records)
        if not news_df.empty and "headline" not in news_df.columns:
            news_df["headline"] = ""
        if not news_df.empty and "created_at" not in news_df.columns:
            news_df["created_at"] = None
        if not news_df.empty and "id" in news_df.columns:
            news_df = news_df.drop_duplicates(subset=["id"])

        sentiment_daily = _build_sentiment_daily(news_df)
        if not bars_df.empty:
            bars_df["date"] = bars_df["timestamp"].dt.date
            merged = bars_df.merge(sentiment_daily, on="date", how="left")
            merged["sentiment_mean"] = merged["sentiment_mean"].fillna(0.0)
            merged["sentiment_count"] = merged["sentiment_count"].fillna(0).astype("int64")
            merged["symbol"] = symbol
            merged = _label_dataset(merged, forward_bars=args.forward_bars)
        else:
            merged = pd.DataFrame()

        safe_symbol = _safe_symbol_filename(symbol)
        bars_path = out_dirs["raw_bars"] / f"{safe_symbol}_{args.timeframe}.csv"
        news_path = out_dirs["raw_news"] / f"{safe_symbol}_news.csv"
        model_path = out_dirs["model_dataset"] / f"{safe_symbol}_dataset.csv"

        bars_df.to_csv(bars_path, index=False)
        news_df.to_csv(news_path, index=False)
        merged.to_csv(model_path, index=False)

        if not merged.empty:
            all_rows.append(merged)

        summary.append(
            {
                "symbol": symbol,
                "news_symbol_query": news_symbol,
                "bars_rows": int(len(bars_df)),
                "news_rows": int(len(news_df)),
                "dataset_rows": int(len(merged)),
                "dataset_labeled_rows": int(merged["forward_return"].notna().sum()) if not merged.empty else 0,
                "start": start,
                "end": end,
                "timeframe": args.timeframe,
                "forward_bars": args.forward_bars,
            }
        )

    combined_path = out_dirs["model_dataset"] / "combined_dataset.csv"
    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        combined.to_csv(combined_path, index=False)
    else:
        pd.DataFrame().to_csv(combined_path, index=False)

    summary_path = Path(args.output_dir) / "collection_summary.json"
    with summary_path.open("w", encoding="utf-8") as fp:
        json.dump(summary, fp, indent=2)

    print(f"Saved summary: {summary_path}")
    print(f"Saved combined dataset: {combined_path}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
