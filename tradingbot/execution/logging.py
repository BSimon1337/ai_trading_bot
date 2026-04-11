from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tradingbot.config.settings import BotConfig

DECISION_HEADERS = [
    "timestamp",
    "mode",
    "symbol",
    "asset_class",
    "action",
    "action_source",
    "model_prob_up",
    "sentiment_probability",
    "sentiment_label",
    "quantity",
    "portfolio_value",
    "cash",
    "reason",
    "result",
]

FILL_HEADERS = [
    "timestamp",
    "mode",
    "symbol",
    "asset_class",
    "side",
    "quantity",
    "order_id",
    "portfolio_value",
    "cash",
    "notional_usd",
    "result",
]

SNAPSHOT_HEADERS = ["date", "mode", "symbol", "portfolio_value", "cash", "position_qty", "day_pnl"]


@dataclass(frozen=True)
class LogPaths:
    decisions: Path
    fills: Path
    snapshot: Path

    @classmethod
    def from_config(cls, config: BotConfig) -> "LogPaths":
        return cls(
            decisions=Path(config.decision_log_path),
            fills=Path(config.fill_log_path),
            snapshot=Path(config.daily_snapshot_path),
        )


def _ensure_csv(path: Path, headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()


def ensure_runtime_logs(paths: LogPaths) -> None:
    _ensure_csv(paths.decisions, DECISION_HEADERS)
    _ensure_csv(paths.fills, FILL_HEADERS)
    _ensure_csv(paths.snapshot, SNAPSHOT_HEADERS)


def _append_row(path: Path, headers: list[str], row: dict[str, Any]) -> None:
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writerow({header: row.get(header, "") for header in headers})


def append_decision_record(paths: LogPaths, row: dict[str, Any]) -> None:
    ensure_runtime_logs(paths)
    _append_row(paths.decisions, DECISION_HEADERS, row)


def append_fill_record(paths: LogPaths, row: dict[str, Any]) -> None:
    ensure_runtime_logs(paths)
    _append_row(paths.fills, FILL_HEADERS, row)


def log_run_event(paths: LogPaths, mode: str, result: str, reason: str) -> None:
    append_decision_record(
        paths,
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "symbol": "SYSTEM",
            "asset_class": "system",
            "action": "hold",
            "action_source": "guardrail",
            "model_prob_up": "",
            "sentiment_probability": "",
            "sentiment_label": "",
            "quantity": 0,
            "portfolio_value": "",
            "cash": "",
            "reason": reason,
            "result": result,
        },
    )
