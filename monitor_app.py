from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Flask, render_template

APP = Flask(__name__)

DECISIONS_PATH = Path("logs/paper_validation/decisions.csv")
FILLS_PATH = Path("logs/paper_validation/fills.csv")
SNAPSHOT_PATH = Path("logs/paper_validation/daily_snapshot.csv")


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


def _dashboard_data() -> dict[str, Any]:
    decisions = _read_csv(DECISIONS_PATH)
    fills = _read_csv(FILLS_PATH)
    snapshot = _read_csv(SNAPSHOT_PATH)

    if not decisions.empty and "timestamp" in decisions.columns:
        decisions["timestamp"] = pd.to_datetime(decisions["timestamp"], errors="coerce", utc=True)
        decisions = decisions.sort_values("timestamp")
    if not fills.empty and "timestamp" in fills.columns:
        fills["timestamp"] = pd.to_datetime(fills["timestamp"], errors="coerce", utc=True)
        fills = fills.sort_values("timestamp")

    latest_decision = decisions.iloc[-1].to_dict() if not decisions.empty else {}
    latest_snapshot = snapshot.iloc[-1].to_dict() if not snapshot.empty else {}

    latest_action = str(latest_decision.get("action", "n/a"))
    latest_reason = str(latest_decision.get("reason", "n/a"))
    latest_source = str(latest_decision.get("action_source", "n/a"))

    portfolio_value = _to_float(latest_snapshot.get("portfolio_value", 0.0))
    day_pnl = _to_float(latest_snapshot.get("day_pnl", 0.0))
    position_qty = _to_float(latest_snapshot.get("position_qty", 0.0))

    decisions_today = 0
    fills_today = 0
    now_utc_date = datetime.now(timezone.utc).date()
    if not decisions.empty and "timestamp" in decisions.columns:
        decisions_today = _to_int((decisions["timestamp"].dt.date == now_utc_date).sum())
    if not fills.empty and "timestamp" in fills.columns:
        fills_today = _to_int((fills["timestamp"].dt.date == now_utc_date).sum())

    recent_decisions = decisions.tail(15).copy() if not decisions.empty else pd.DataFrame()
    recent_fills = fills.tail(15).copy() if not fills.empty else pd.DataFrame()
    recent_snapshot = snapshot.tail(30).copy() if not snapshot.empty else pd.DataFrame()

    if not recent_decisions.empty:
        recent_decisions["timestamp"] = recent_decisions["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    if not recent_fills.empty:
        recent_fills["timestamp"] = recent_fills["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")

    last_decision_ts = None
    heartbeat_age_minutes = None
    if not decisions.empty and "timestamp" in decisions.columns:
        last_decision_ts = decisions["timestamp"].iloc[-1]
        if pd.notna(last_decision_ts):
            heartbeat_age_minutes = float((datetime.now(timezone.utc) - last_decision_ts.to_pydatetime()).total_seconds() / 60.0)

    if last_decision_ts is None:
        status = "no_data"
    elif heartbeat_age_minutes is not None and heartbeat_age_minutes > 180:
        status = "stale"
    else:
        status = "running"

    pnl_points = []
    equity_points = []
    if not recent_snapshot.empty:
        recent_snapshot["portfolio_value"] = pd.to_numeric(recent_snapshot["portfolio_value"], errors="coerce")
        recent_snapshot["day_pnl"] = pd.to_numeric(recent_snapshot["day_pnl"], errors="coerce")
        recent_snapshot = recent_snapshot.fillna(0)
        equity_points = recent_snapshot["portfolio_value"].astype(float).tolist()
        pnl_points = recent_snapshot["day_pnl"].astype(float).tolist()

    actions_7d = {"buy": 0, "sell": 0, "hold": 0, "flat": 0}
    if not decisions.empty and "action" in decisions.columns and "timestamp" in decisions.columns:
        d7 = decisions[decisions["timestamp"] >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)]
        if not d7.empty:
            counts = d7["action"].astype(str).value_counts().to_dict()
            for key in actions_7d:
                actions_7d[key] = int(counts.get(key, 0))

    return {
        "status": status,
        "status_updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "heartbeat_age_minutes": heartbeat_age_minutes,
        "portfolio_value": portfolio_value,
        "day_pnl": day_pnl,
        "position_qty": position_qty,
        "latest_action": latest_action,
        "latest_reason": latest_reason,
        "latest_source": latest_source,
        "decisions_today": decisions_today,
        "fills_today": fills_today,
        "recent_decisions_columns": list(recent_decisions.columns),
        "recent_decisions_rows": recent_decisions.fillna("").to_dict(orient="records"),
        "recent_fills_columns": list(recent_fills.columns),
        "recent_fills_rows": recent_fills.fillna("").to_dict(orient="records"),
        "equity_points": equity_points,
        "pnl_points": pnl_points,
        "actions_7d": actions_7d,
    }


@APP.route("/")
def dashboard():
    return render_template("monitor.html", **_dashboard_data())


@APP.route("/health")
def health():
    return {"ok": True, "time_utc": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    APP.run(host="0.0.0.0", port=8080, debug=False)
