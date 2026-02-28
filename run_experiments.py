from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from utils import setup_logging

plt.switch_backend("Agg")

TECH_FEATURES = ["ret_1", "sma_20", "ema_20", "rsi_14", "volume_z20"]
SENTIMENT_FEATURES = ["sentiment_mean", "sentiment_count"]
FEATURES = TECH_FEATURES + SENTIMENT_FEATURES


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    risk_fraction: float
    long_threshold: float
    allow_short: bool


DEFAULT_CONFIGS: List[ExperimentConfig] = [
    ExperimentConfig(name="conservative", risk_fraction=0.25, long_threshold=0.58, allow_short=False),
    ExperimentConfig(name="medium", risk_fraction=0.50, long_threshold=0.55, allow_short=False),
    ExperimentConfig(name="aggressive", risk_fraction=0.90, long_threshold=0.52, allow_short=True),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run class-ready experiment matrix and generate final artifacts.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["SPY", "BTCUSD"],
        help="Symbols to evaluate. Example: SPY BTCUSD ETHUSD",
    )
    parser.add_argument("--start", default="2024-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD")
    parser.add_argument("--model-path", default="models/xgb_full.joblib", help="Trained model path")
    parser.add_argument(
        "--dataset-dir",
        default="data/model_dataset",
        help="Directory containing symbol datasets like SPY_dataset.csv",
    )
    parser.add_argument("--reports-dir", default="reports", help="Output reports directory")
    return parser.parse_args()


def _max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1.0 + returns).cumprod()
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    return float(drawdown.min())


def _sharpe(returns: pd.Series, periods_per_year: int = 252) -> float:
    if returns.empty:
        return 0.0
    std = returns.std(ddof=0)
    if std == 0 or np.isnan(std):
        return 0.0
    return float(np.sqrt(periods_per_year) * (returns.mean() / std))


def _cagr(total_return: float, periods: int, periods_per_year: int = 252) -> float:
    if periods <= 0:
        return 0.0
    years = periods / periods_per_year
    if years <= 0:
        return 0.0
    return (1.0 + total_return) ** (1.0 / years) - 1.0


def _load_symbol_dataset(dataset_dir: Path, symbol: str, start: str, end: str) -> pd.DataFrame:
    path = dataset_dir / f"{symbol}_dataset.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found for {symbol}: {path}")

    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Dataset is empty for {symbol}: {path}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"]).copy()
    df = df[df["symbol"] == symbol].copy()
    df["forward_return"] = pd.to_numeric(df["forward_return"], errors="coerce")
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    start_ts = pd.to_datetime(start, utc=True)
    end_ts = pd.to_datetime(end, utc=True)
    df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)].copy()
    df = df.dropna(subset=["forward_return"]).sort_values("timestamp").reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No usable rows for {symbol} in requested window.")
    return df


def _run_single_config(df: pd.DataFrame, model, config: ExperimentConfig) -> pd.DataFrame:
    out = df.copy()
    if hasattr(model, "predict_proba"):
        out["prob_up"] = model.predict_proba(out[["symbol"] + FEATURES])[:, 1]
    else:
        out["prob_up"] = model.predict(out[["symbol"] + FEATURES]).astype(float)

    short_threshold = 1.0 - config.long_threshold
    signal = np.where(out["prob_up"] >= config.long_threshold, 1, 0)
    if config.allow_short:
        signal = np.where(out["prob_up"] <= short_threshold, -1, signal)
    out["signal"] = signal.astype(int)

    out["strategy_return"] = out["signal"] * out["forward_return"] * config.risk_fraction
    out["benchmark_return"] = out["forward_return"]
    out["strategy_equity"] = (1.0 + out["strategy_return"]).cumprod()
    out["benchmark_equity"] = (1.0 + out["benchmark_return"]).cumprod()
    return out


def _build_metrics(symbol: str, config: ExperimentConfig, rows: pd.DataFrame) -> Dict[str, float | str]:
    strategy_returns = rows["strategy_return"]
    benchmark_returns = rows["benchmark_return"]
    strategy_total_return = float(rows["strategy_equity"].iloc[-1] - 1.0)
    benchmark_total_return = float(rows["benchmark_equity"].iloc[-1] - 1.0)
    trade_events = int((rows["signal"].diff().abs().fillna(0) > 0).sum())
    active = rows[rows["signal"] != 0]
    win_rate = float((active["strategy_return"] > 0).mean()) if not active.empty else 0.0

    return {
        "symbol": symbol,
        "config": config.name,
        "rows": int(len(rows)),
        "risk_fraction": config.risk_fraction,
        "long_threshold": config.long_threshold,
        "allow_short": config.allow_short,
        "total_return_pct": strategy_total_return * 100.0,
        "benchmark_return_pct": benchmark_total_return * 100.0,
        "cagr_pct": _cagr(strategy_total_return, len(rows)) * 100.0,
        "benchmark_cagr_pct": _cagr(benchmark_total_return, len(rows)) * 100.0,
        "sharpe": _sharpe(strategy_returns),
        "benchmark_sharpe": _sharpe(benchmark_returns),
        "max_drawdown_pct": _max_drawdown(strategy_returns) * 100.0,
        "benchmark_max_drawdown_pct": _max_drawdown(benchmark_returns) * 100.0,
        "trade_events": trade_events,
        "win_rate_pct": win_rate * 100.0,
    }


def _plot_equity_curves(
    all_runs: Dict[str, Dict[str, pd.DataFrame]],
    symbols: List[str],
    output_path: Path,
) -> None:
    fig, axes = plt.subplots(len(symbols), 1, figsize=(12, 4 * len(symbols)), sharex=False)
    if len(symbols) == 1:
        axes = [axes]

    for ax, symbol in zip(axes, symbols):
        symbol_runs = all_runs[symbol]
        benchmark = None
        for config_name, df in symbol_runs.items():
            if benchmark is None:
                benchmark = df[["timestamp", "benchmark_equity"]].copy()
            ax.plot(df["timestamp"], df["strategy_equity"], label=f"{config_name} strategy", linewidth=1.8)

        if benchmark is not None:
            ax.plot(
                benchmark["timestamp"],
                benchmark["benchmark_equity"],
                label=f"{symbol} buy&hold",
                linewidth=2.2,
                linestyle="--",
                color="black",
            )
        ax.set_title(f"Equity Curves - {symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity (start=1.0)")
        ax.grid(alpha=0.3)
        ax.legend()

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=170)
    plt.close(fig)


def _write_notes(reports_dir: Path, symbols: List[str], start: str, end: str, model_path: str) -> None:
    methodology = (
        "# Methodology Notes\n\n"
        f"- Evaluation window: {start} to {end}\n"
        f"- Symbols: {', '.join(symbols)}\n"
        f"- Model used: `{model_path}`\n"
        "- Signals are generated from model probability (`prob_up`) with configuration-specific thresholds.\n"
        "- Strategy return per row = `signal * forward_return * risk_fraction`.\n"
        "- Config matrix compares conservative/medium/aggressive risk and threshold settings.\n"
        "- Benchmark is buy-and-hold using each symbol's `forward_return`.\n"
    )
    limitations = (
        "# Limitations\n\n"
        "- This experiment uses prebuilt dataset rows and model predictions, not full exchange order-book replay.\n"
        "- Fill quality, latency, and slippage are not fully modeled in this matrix.\n"
        "- Regime changes can reduce future performance relative to the test window.\n"
        "- Results should be treated as comparative evidence across configs, not guaranteed future outcomes.\n"
        "- Paper/live execution can diverge from offline simulation due to API timing and market microstructure.\n"
    )
    (reports_dir / "methodology_notes.md").write_text(methodology, encoding="utf-8")
    (reports_dir / "limitations.md").write_text(limitations, encoding="utf-8")


def main() -> None:
    setup_logging()
    args = parse_args()
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    dataset_dir = Path(args.dataset_dir)
    model_path = Path(args.model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = joblib.load(model_path)
    symbols = [s.upper() for s in args.symbols]
    metrics_rows: List[Dict[str, float | str]] = []
    all_runs: Dict[str, Dict[str, pd.DataFrame]] = {}

    for symbol in symbols:
        symbol_df = _load_symbol_dataset(dataset_dir, symbol, args.start, args.end)
        all_runs[symbol] = {}
        for config in DEFAULT_CONFIGS:
            run_df = _run_single_config(symbol_df, model, config)
            metrics_rows.append(_build_metrics(symbol, config, run_df))
            all_runs[symbol][config.name] = run_df

    metrics_df = pd.DataFrame(metrics_rows).sort_values(["symbol", "config"]).reset_index(drop=True)
    metrics_path = reports_dir / "final_metrics_table.csv"
    metrics_df.to_csv(metrics_path, index=False)

    curves_path = reports_dir / "final_equity_curves.png"
    _plot_equity_curves(all_runs, symbols, curves_path)
    _write_notes(reports_dir, symbols, args.start, args.end, args.model_path)

    print(f"Saved metrics table: {metrics_path}")
    print(f"Saved equity curves: {curves_path}")
    print(f"Saved methodology notes: {reports_dir / 'methodology_notes.md'}")
    print(f"Saved limitations: {reports_dir / 'limitations.md'}")
    print("\n=== Final Metrics Preview ===")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
