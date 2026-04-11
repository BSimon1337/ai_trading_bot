from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, render_template

APP = Flask(__name__)

INSTANCE_PATHS = {
    "SPY": {
        "decisions": Path("logs/paper_validation/decisions.csv"),
        "fills": Path("logs/paper_validation/fills.csv"),
        "snapshot": Path("logs/paper_validation/daily_snapshot.csv"),
    },
    "BTCUSD": {
        "decisions": Path("logs/paper_validation_btc/decisions.csv"),
        "fills": Path("logs/paper_validation_btc/fills.csv"),
        "snapshot": Path("logs/paper_validation_btc/daily_snapshot.csv"),
    },
}


def _configured_instance_paths() -> dict[str, dict[str, Path]]:
    symbols = [symbol.strip().upper() for symbol in os.getenv("SYMBOLS", "").split(",") if symbol.strip()]
    if not symbols:
        return INSTANCE_PATHS

    paths: dict[str, dict[str, Path]] = {}
    for symbol in symbols:
        suffix = "" if symbol == "SPY" else f"_{symbol.lower().replace('/', '').replace('-', '')}"
        paths[symbol] = {
            "decisions": Path(f"logs/paper_validation{suffix}/decisions.csv"),
            "fills": Path(f"logs/paper_validation{suffix}/fills.csv"),
            "snapshot": Path(f"logs/paper_validation{suffix}/daily_snapshot.csv"),
        }
    return paths


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _format_recent(df: pd.DataFrame, limit: int = 15) -> tuple[list[str], list[dict[str, Any]]]:
    recent = df.tail(limit).copy() if not df.empty else pd.DataFrame()
    if recent.empty:
        return [], []
    if "timestamp" in recent.columns and pd.api.types.is_datetime64_any_dtype(recent["timestamp"]):
        recent["timestamp"] = recent["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return list(recent.columns), recent.fillna("").to_dict(orient="records")


def _instance_data(label: str, paths: dict[str, Path]) -> dict[str, Any]:
    decisions = _read_csv(paths["decisions"])
    fills = _read_csv(paths["fills"])
    snapshot = _read_csv(paths["snapshot"])

    if not decisions.empty and "timestamp" in decisions.columns:
        decisions["timestamp"] = pd.to_datetime(decisions["timestamp"], errors="coerce", utc=True)
        decisions = decisions.sort_values("timestamp")
    if not fills.empty and "timestamp" in fills.columns:
        fills["timestamp"] = pd.to_datetime(fills["timestamp"], errors="coerce", utc=True)
        fills = fills.sort_values("timestamp")

    latest_decision = decisions.iloc[-1].to_dict() if not decisions.empty else {}
    latest_snapshot = snapshot.iloc[-1].to_dict() if not snapshot.empty else {}
    latest_mode = str(latest_decision.get("mode", "unknown"))
    latest_asset_class = str(latest_decision.get("asset_class", "unknown"))

    last_decision_ts = None
    heartbeat_age_minutes = None
    if not decisions.empty and "timestamp" in decisions.columns:
        last_decision_ts = decisions["timestamp"].iloc[-1]
        if pd.notna(last_decision_ts):
            heartbeat_age_minutes = float(
                (datetime.now(timezone.utc) - last_decision_ts.to_pydatetime()).total_seconds() / 60.0
            )

    if latest_mode == "blocked-live":
        status = "blocked_live"
    elif latest_mode == "active-live":
        status = "live"
    elif latest_mode == "paper":
        status = "paper"
    elif last_decision_ts is None:
        status = "no_data"
    elif heartbeat_age_minutes is not None and heartbeat_age_minutes > 180:
        status = "stale"
    else:
        status = "running"

    now_utc_date = datetime.now(timezone.utc).date()
    decisions_today = 0
    fills_today = 0
    if not decisions.empty and "timestamp" in decisions.columns:
        decisions_today = _to_int((decisions["timestamp"].dt.date == now_utc_date).sum())
    if not fills.empty and "timestamp" in fills.columns:
        fills_today = _to_int((fills["timestamp"].dt.date == now_utc_date).sum())

    equity_points: list[float] = []
    pnl_points: list[float] = []
    if not snapshot.empty:
        snapshot = snapshot.copy()
        snapshot["portfolio_value"] = pd.to_numeric(snapshot.get("portfolio_value"), errors="coerce")
        snapshot["day_pnl"] = pd.to_numeric(snapshot.get("day_pnl"), errors="coerce")
        snapshot = snapshot.fillna(0)
        equity_points = snapshot["portfolio_value"].astype(float).tail(30).tolist()
        pnl_points = snapshot["day_pnl"].astype(float).tail(30).tolist()

    actions_7d = {"buy": 0, "sell": 0, "hold": 0, "flat": 0}
    if not decisions.empty and "action" in decisions.columns and "timestamp" in decisions.columns:
        d7 = decisions[decisions["timestamp"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)]
        if not d7.empty:
            counts = d7["action"].astype(str).value_counts().to_dict()
            for key in actions_7d:
                actions_7d[key] = int(counts.get(key, 0))

    decision_columns, decision_rows = _format_recent(decisions, limit=15)
    fill_columns, fill_rows = _format_recent(fills, limit=15)

    return {
        "label": label,
        "status": status,
        "heartbeat_age_minutes": heartbeat_age_minutes,
        "portfolio_value": _to_float(latest_snapshot.get("portfolio_value", 0.0)),
        "day_pnl": _to_float(latest_snapshot.get("day_pnl", 0.0)),
        "position_qty": _to_float(latest_snapshot.get("position_qty", 0.0)),
        "latest_action": str(latest_decision.get("action", "n/a")),
        "latest_mode": latest_mode,
        "latest_asset_class": latest_asset_class,
        "latest_reason": str(latest_decision.get("reason", "n/a")),
        "latest_source": str(latest_decision.get("action_source", "n/a")),
        "decisions_today": decisions_today,
        "fills_today": fills_today,
        "equity_points": equity_points,
        "pnl_points": pnl_points,
        "actions_7d": actions_7d,
        "recent_decisions_columns": decision_columns,
        "recent_decisions_rows": decision_rows,
        "recent_fills_columns": fill_columns,
        "recent_fills_rows": fill_rows,
    }


def _dashboard_data() -> dict[str, Any]:
    instances = [_instance_data(label, paths) for label, paths in _configured_instance_paths().items()]
    available_instances = [item["label"] for item in instances]
    active_label = available_instances[0] if available_instances else ""
    active_instance = next((item for item in instances if item["label"] == active_label), {})

    return {
        "instances": instances,
        "available_instances": available_instances,
        "active_instance": active_instance,
        "status_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


@APP.route("/")
def dashboard():
    return render_template("monitor.html", **_dashboard_data())


@APP.route("/health")
def health():
    return {"ok": True, "time_utc": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8080, debug=False)
