from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tradingbot.execution.logging import DECISION_HEADERS, FILL_HEADERS, SNAPSHOT_HEADERS


def _write_rows(path: Path, headers: list[str], rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, "") for header in headers})
    return path


def write_decisions(path: Path, rows: list[dict[str, object]]) -> Path:
    return _write_rows(path, DECISION_HEADERS, rows)


def write_fills(path: Path, rows: list[dict[str, object]]) -> Path:
    return _write_rows(path, FILL_HEADERS, rows)


def write_snapshots(path: Path, rows: list[dict[str, object]]) -> Path:
    return _write_rows(path, SNAPSHOT_HEADERS, rows)


def recent_decision(symbol: str = "SPY", **overrides) -> dict[str, object]:
    row: dict[str, object] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "paper",
        "symbol": symbol,
        "asset_class": "crypto" if "/" in symbol else "stock",
        "action": "hold",
        "action_source": "model",
        "model_prob_up": "0.51",
        "sentiment_source": "external",
        "sentiment_probability": "0.0",
        "sentiment_label": "neutral",
        "quantity": "0",
        "portfolio_value": "100.0",
        "cash": "100.0",
        "reason": "no_signal",
        "result": "skipped",
    }
    row.update(overrides)
    return row


def healthy_decision(symbol: str = "SPY", **overrides) -> dict[str, object]:
    return recent_decision(symbol=symbol, mode="paper", reason="no_signal", result="skipped", **overrides)


def blocked_live_decision(symbol: str = "SYSTEM", **overrides) -> dict[str, object]:
    return recent_decision(
        symbol=symbol,
        mode="blocked-live",
        asset_class="system",
        action_source="guardrail",
        reason="Live trading is blocked.",
        result="blocked",
        **overrides,
    )


def failed_run_decision(symbol: str = "SYSTEM", **overrides) -> dict[str, object]:
    return recent_decision(
        symbol=symbol,
        mode="active-live",
        asset_class="system",
        action_source="guardrail",
        reason="Runtime failed.",
        result="failed",
        **overrides,
    )


def stale_decision(symbol: str = "SPY", minutes_old: int = 240, **overrides) -> dict[str, object]:
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_old)
    return recent_decision(symbol=symbol, timestamp=timestamp.isoformat(), **overrides)


def broker_rejection(symbol: str = "BTC/USD", **overrides) -> dict[str, object]:
    return recent_decision(
        symbol=symbol,
        mode="live",
        action="hold",
        reason="broker_rejected",
        result="skipped",
        **overrides,
    )


def write_malformed_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('timestamp,symbol,action\n"unterminated,BTC/USD,buy\n', encoding="utf-8")
    return path


def create_monitor_fixture(root: Path, state: str, symbol: str = "SPY") -> dict[str, Path]:
    paths = {
        "decisions": root / "decisions.csv",
        "fills": root / "fills.csv",
        "snapshot": root / "daily_snapshot.csv",
    }
    if state == "no_data":
        root.mkdir(parents=True, exist_ok=True)
        return paths
    if state == "malformed":
        write_malformed_csv(paths["decisions"])
        return paths

    decision_factories = {
        "healthy": healthy_decision,
        "stale": stale_decision,
        "blocked_live": blocked_live_decision,
        "failed": failed_run_decision,
        "broker_rejection": broker_rejection,
    }
    try:
        decision = decision_factories[state](symbol=symbol)
    except KeyError as exc:
        raise ValueError(f"Unknown monitor fixture state: {state}") from exc

    write_decisions(paths["decisions"], [decision])
    write_fills(paths["fills"], [])
    write_snapshots(
        paths["snapshot"],
        [
            {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "mode": decision.get("mode", "paper"),
                "symbol": symbol,
                "portfolio_value": "100",
                "cash": "100",
                "position_qty": "0",
                "day_pnl": "0",
            }
        ],
    )
    return paths
