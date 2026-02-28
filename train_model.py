from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

from utils import setup_logging

TECH_FEATURES = ["ret_1", "sma_20", "ema_20", "rsi_14", "volume_z20"]
SENTIMENT_FEATURES = ["sentiment_mean", "sentiment_count"]
TARGET_COL = "target_up"
RET_COL = "forward_return"
TIMESTAMP_COL = "timestamp"
SYMBOL_COL = "symbol"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train and evaluate baseline ML models.")
    parser.add_argument(
        "--dataset",
        default="data/model_dataset/combined_dataset.csv",
        help="Path to combined dataset CSV.",
    )
    parser.add_argument(
        "--models-dir",
        default="models",
        help="Directory to save trained model artifacts.",
    )
    parser.add_argument(
        "--reports-dir",
        default="reports",
        help="Directory to save metrics and predictions.",
    )
    parser.add_argument(
        "--n-splits",
        type=int,
        default=5,
        help="Number of time-series CV splits.",
    )
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


def _strategy_metrics(y_true: pd.Series, y_pred: pd.Series, forward_ret: pd.Series) -> Dict[str, float]:
    strategy_returns = forward_ret * y_pred.astype(float)
    benchmark_returns = forward_ret

    metrics: Dict[str, float] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "strategy_cum_return": float((1.0 + strategy_returns).prod() - 1.0),
        "benchmark_cum_return": float((1.0 + benchmark_returns).prod() - 1.0),
        "strategy_sharpe": _sharpe(strategy_returns),
        "benchmark_sharpe": _sharpe(benchmark_returns),
        "strategy_max_drawdown": _max_drawdown(strategy_returns),
        "benchmark_max_drawdown": _max_drawdown(benchmark_returns),
        "n_obs": int(len(y_true)),
    }
    if y_true.nunique() > 1:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_pred))
    else:
        metrics["roc_auc"] = float("nan")
    return metrics


def _build_pipeline(model_name: str, feature_cols: List[str]) -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    preprocess = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, feature_cols),
            ("symbol", OneHotEncoder(handle_unknown="ignore"), [SYMBOL_COL]),
        ],
        remainder="drop",
    )

    if model_name.startswith("logreg"):
        model = LogisticRegression(max_iter=2000, class_weight="balanced")
    elif model_name == "xgb_full":
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
    else:
        raise ValueError(f"Unknown model name: {model_name}")
    return Pipeline(steps=[("preprocess", preprocess), ("model", model)])


def _prepare_df(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f"Dataset is empty: {path}")

    required = {TIMESTAMP_COL, SYMBOL_COL, TARGET_COL, RET_COL}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {sorted(missing)}")

    df[TIMESTAMP_COL] = pd.to_datetime(df[TIMESTAMP_COL], utc=True, errors="coerce")
    df = df.dropna(subset=[TIMESTAMP_COL, TARGET_COL, RET_COL]).copy()
    df[TARGET_COL] = pd.to_numeric(df[TARGET_COL], errors="coerce")
    df[RET_COL] = pd.to_numeric(df[RET_COL], errors="coerce")
    df = df.dropna(subset=[TARGET_COL, RET_COL]).copy()
    df[TARGET_COL] = df[TARGET_COL].astype(int)
    df = df.sort_values(TIMESTAMP_COL).reset_index(drop=True)
    return df


def main() -> None:
    setup_logging()
    args = parse_args()

    dataset_path = Path(args.dataset)
    models_dir = Path(args.models_dir)
    reports_dir = Path(args.reports_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    df = _prepare_df(dataset_path)
    model_specs = [
        ("logreg_tech", TECH_FEATURES),
        ("logreg_full", TECH_FEATURES + SENTIMENT_FEATURES),
        ("xgb_full", TECH_FEATURES + SENTIMENT_FEATURES),
    ]

    tscv = TimeSeriesSplit(n_splits=args.n_splits)
    rows: List[Dict[str, float]] = []
    pred_rows: List[pd.DataFrame] = []

    for model_name, feature_cols in model_specs:
        model_df = df[[TIMESTAMP_COL, SYMBOL_COL, TARGET_COL, RET_COL] + feature_cols].copy()
        model_df[feature_cols] = model_df[feature_cols].apply(pd.to_numeric, errors="coerce")
        model_df = model_df.dropna(subset=[TARGET_COL, RET_COL]).reset_index(drop=True)

        for split_idx, (train_idx, test_idx) in enumerate(tscv.split(model_df), start=1):
            train_df = model_df.iloc[train_idx]
            test_df = model_df.iloc[test_idx]
            if len(test_df) == 0:
                continue

            pipe = _build_pipeline(model_name, feature_cols)
            pipe.fit(train_df[[SYMBOL_COL] + feature_cols], train_df[TARGET_COL])
            y_pred = pipe.predict(test_df[[SYMBOL_COL] + feature_cols])

            split_metrics = _strategy_metrics(
                y_true=test_df[TARGET_COL],
                y_pred=pd.Series(y_pred, index=test_df.index),
                forward_ret=test_df[RET_COL],
            )
            split_metrics.update(
                {
                    "model": model_name,
                    "split": split_idx,
                    "train_rows": int(len(train_df)),
                    "test_rows": int(len(test_df)),
                }
            )
            rows.append(split_metrics)

            if hasattr(pipe.named_steps["model"], "predict_proba"):
                y_prob = pipe.predict_proba(test_df[[SYMBOL_COL] + feature_cols])[:, 1]
            else:
                y_prob = y_pred.astype(float)

            preds_df = pd.DataFrame(
                {
                    TIMESTAMP_COL: test_df[TIMESTAMP_COL].values,
                    SYMBOL_COL: test_df[SYMBOL_COL].values,
                    "model": model_name,
                    "split": split_idx,
                    "y_true": test_df[TARGET_COL].values,
                    "y_pred": y_pred,
                    "y_prob_up": y_prob,
                    RET_COL: test_df[RET_COL].values,
                    "strategy_return": test_df[RET_COL].values * y_pred,
                    "benchmark_return": test_df[RET_COL].values,
                }
            )
            pred_rows.append(preds_df)

        final_pipe = _build_pipeline(model_name, feature_cols)
        final_pipe.fit(model_df[[SYMBOL_COL] + feature_cols], model_df[TARGET_COL])
        joblib.dump(final_pipe, models_dir / f"{model_name}.joblib")

    metrics_df = pd.DataFrame(rows)
    preds_all = pd.concat(pred_rows, ignore_index=True) if pred_rows else pd.DataFrame()
    summary_df = (
        metrics_df.groupby("model", as_index=False)[
            [
                "accuracy",
                "f1",
                "roc_auc",
                "strategy_cum_return",
                "benchmark_cum_return",
                "strategy_sharpe",
                "benchmark_sharpe",
                "strategy_max_drawdown",
                "benchmark_max_drawdown",
                "test_rows",
            ]
        ]
        .mean(numeric_only=True)
        .rename(columns={"test_rows": "avg_test_rows"})
    )

    metrics_path = reports_dir / "model_metrics_by_split.csv"
    summary_path = reports_dir / "model_metrics_summary.csv"
    preds_path = reports_dir / "predictions_walkforward.csv"
    metadata_path = reports_dir / "training_metadata.json"

    metrics_df.to_csv(metrics_path, index=False)
    summary_df.to_csv(summary_path, index=False)
    preds_all.to_csv(preds_path, index=False)
    metadata_path.write_text(
        json.dumps(
            {
                "dataset": str(dataset_path),
                "rows_total": int(len(df)),
                "models": [name for name, _ in model_specs],
                "features_technical": TECH_FEATURES,
                "features_sentiment": SENTIMENT_FEATURES,
                "n_splits": args.n_splits,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Saved split metrics: {metrics_path}")
    print(f"Saved summary metrics: {summary_path}")
    print(f"Saved predictions: {preds_path}")
    print(f"Saved model artifacts in: {models_dir}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()
