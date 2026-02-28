from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from utils import setup_logging

plt.switch_backend("Agg")

TECH_FEATURES = ["ret_1", "sma_20", "ema_20", "rsi_14", "volume_z20"]
SENTIMENT_FEATURES = ["sentiment_mean", "sentiment_count"]
FEATURES = TECH_FEATURES + SENTIMENT_FEATURES
TARGET_COL = "target_up"
RET_COL = "forward_return"
TS_COL = "timestamp"
SYMBOL_COL = "symbol"


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
    parser = argparse.ArgumentParser(
        description="Strict out-of-sample experiments (train window vs unseen test window)."
    )
    parser.add_argument("--symbols", nargs="+", default=["SPY", "BTCUSD"])
    parser.add_argument("--dataset", default="data/model_dataset/combined_dataset.csv")
    parser.add_argument("--train-start", default="2022-01-01")
    parser.add_argument("--train-end", default="2023-12-31")
    parser.add_argument("--test-start", default="2024-01-01")
    parser.add_argument("--test-end", default="2024-12-31")
    parser.add_argument("--reports-dir", default="reports")
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


def _build_model() -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, FEATURES),
            ("symbol", OneHotEncoder(handle_unknown="ignore"), [SYMBOL_COL]),
        ],
        remainder="drop",
    )
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        eval_metric="logloss",
        n_jobs=4,
    )
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def _load_data(path: Path, symbols: List[str]) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Dataset empty: {path}")
    df[TS_COL] = pd.to_datetime(df[TS_COL], utc=True, errors="coerce")
    df = df.dropna(subset=[TS_COL]).copy()
    df = df[df[SYMBOL_COL].isin(symbols)].copy()
    for col in FEATURES + [TARGET_COL, RET_COL]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET_COL, RET_COL]).copy()
    df[TARGET_COL] = df[TARGET_COL].astype(int)
    df = df.sort_values(TS_COL).reset_index(drop=True)
    if df.empty:
        raise ValueError("No usable rows after filtering.")
    return df


def _run_single_config(df: pd.DataFrame, config: ExperimentConfig) -> pd.DataFrame:
    out = df.copy()
    short_threshold = 1.0 - config.long_threshold
    signal = np.where(out["prob_up"] >= config.long_threshold, 1, 0)
    if config.allow_short:
        signal = np.where(out["prob_up"] <= short_threshold, -1, signal)
    out["signal"] = signal.astype(int)
    out["strategy_return"] = out["signal"] * out[RET_COL] * config.risk_fraction
    out["benchmark_return"] = out[RET_COL]
    out["strategy_equity"] = (1.0 + out["strategy_return"]).cumprod()
    out["benchmark_equity"] = (1.0 + out["benchmark_return"]).cumprod()
    return out


def _metrics(symbol: str, config: ExperimentConfig, rows: pd.DataFrame) -> Dict[str, float | str]:
    strategy_total = float(rows["strategy_equity"].iloc[-1] - 1.0)
    bench_total = float(rows["benchmark_equity"].iloc[-1] - 1.0)
    active = rows[rows["signal"] != 0]
    win_rate = float((active["strategy_return"] > 0).mean()) if not active.empty else 0.0
    trade_events = int((rows["signal"].diff().abs().fillna(0) > 0).sum())
    return {
        "symbol": symbol,
        "config": config.name,
        "rows": int(len(rows)),
        "risk_fraction": config.risk_fraction,
        "long_threshold": config.long_threshold,
        "allow_short": config.allow_short,
        "total_return_pct": strategy_total * 100.0,
        "benchmark_return_pct": bench_total * 100.0,
        "cagr_pct": _cagr(strategy_total, len(rows)) * 100.0,
        "benchmark_cagr_pct": _cagr(bench_total, len(rows)) * 100.0,
        "sharpe": _sharpe(rows["strategy_return"]),
        "benchmark_sharpe": _sharpe(rows["benchmark_return"]),
        "max_drawdown_pct": _max_drawdown(rows["strategy_return"]) * 100.0,
        "benchmark_max_drawdown_pct": _max_drawdown(rows["benchmark_return"]) * 100.0,
        "trade_events": trade_events,
        "win_rate_pct": win_rate * 100.0,
    }


def _plot_curves(all_runs: Dict[str, Dict[str, pd.DataFrame]], output: Path) -> None:
    symbols = list(all_runs.keys())
    fig, axes = plt.subplots(len(symbols), 1, figsize=(12, 4 * len(symbols)))
    if len(symbols) == 1:
        axes = [axes]

    for ax, symbol in zip(axes, symbols):
        benchmark = None
        for cfg_name, df in all_runs[symbol].items():
            ax.plot(df[TS_COL], df["strategy_equity"], label=f"{cfg_name} strategy", linewidth=1.8)
            if benchmark is None:
                benchmark = df[[TS_COL, "benchmark_equity"]]
        if benchmark is not None:
            ax.plot(
                benchmark[TS_COL],
                benchmark["benchmark_equity"],
                label=f"{symbol} buy&hold",
                color="black",
                linestyle="--",
                linewidth=2.1,
            )
        ax.set_title(f"OOS Equity Curves - {symbol}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity (start=1.0)")
        ax.grid(alpha=0.3)
        ax.legend()
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=170)
    plt.close(fig)


def main() -> None:
    setup_logging()
    args = parse_args()
    symbols = [s.upper() for s in args.symbols]
    reports = Path(args.reports_dir)
    reports.mkdir(parents=True, exist_ok=True)

    df = _load_data(Path(args.dataset), symbols)
    train_start = pd.to_datetime(args.train_start, utc=True)
    train_end = pd.to_datetime(args.train_end, utc=True)
    test_start = pd.to_datetime(args.test_start, utc=True)
    test_end = pd.to_datetime(args.test_end, utc=True)

    train_df = df[(df[TS_COL] >= train_start) & (df[TS_COL] <= train_end)].copy()
    test_df = df[(df[TS_COL] >= test_start) & (df[TS_COL] <= test_end)].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Train or test split is empty; adjust dates.")

    model = _build_model()
    model.fit(train_df[[SYMBOL_COL] + FEATURES], train_df[TARGET_COL])

    test_df = test_df.copy()
    test_df["prob_up"] = model.predict_proba(test_df[[SYMBOL_COL] + FEATURES])[:, 1]

    rows: List[Dict[str, float | str]] = []
    all_runs: Dict[str, Dict[str, pd.DataFrame]] = {}
    for symbol in symbols:
        symbol_test = test_df[test_df[SYMBOL_COL] == symbol].copy()
        if symbol_test.empty:
            continue
        all_runs[symbol] = {}
        for cfg in DEFAULT_CONFIGS:
            run_df = _run_single_config(symbol_test, cfg)
            rows.append(_metrics(symbol, cfg, run_df))
            all_runs[symbol][cfg.name] = run_df

    metrics_df = pd.DataFrame(rows).sort_values(["symbol", "config"]).reset_index(drop=True)
    metrics_path = reports / "final_metrics_oos.csv"
    metrics_df.to_csv(metrics_path, index=False)

    curves_path = reports / "final_equity_curves_oos.png"
    _plot_curves(all_runs, curves_path)

    notes = (
        "# OOS Split\n\n"
        f"- Train: {args.train_start} to {args.train_end}\n"
        f"- Test (unseen): {args.test_start} to {args.test_end}\n"
        f"- Symbols: {', '.join(symbols)}\n"
        "- Model: XGBoost (retrained only on train window)\n"
    )
    (reports / "oos_notes.md").write_text(notes, encoding="utf-8")

    print(f"Saved OOS metrics: {metrics_path}")
    print(f"Saved OOS curves: {curves_path}")
    print(f"Saved OOS notes: {reports / 'oos_notes.md'}")
    print("\n=== OOS Metrics Preview ===")
    print(metrics_df.to_string(index=False))


if __name__ == "__main__":
    main()
