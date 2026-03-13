from __future__ import annotations

import csv
import logging
from datetime import date
from math import floor
from pathlib import Path

import joblib
import pandas as pd
from lumibot.strategies.strategy import Strategy
from pandas import Timedelta

from data_handler import DataHandler
from finbert_utils import estimate_sentiment, score_headlines
from portfolio import RiskLimits, RiskManager

LOGGER = logging.getLogger(__name__)


class SentimentMLStrategy(Strategy):
    def initialize(
        self,
        symbol: str = "SPY",
        cash_at_risk: float = 0.20,
        sentiment_probability_threshold: float = 0.70,
        max_position_pct: float = 0.25,
        max_gross_leverage: float = 1.00,
        allow_short: bool = False,
        daily_loss_limit_pct: float = 0.03,
        slippage_bps: float = 5.0,
        commission_per_share: float = 0.0,
        use_model_signal: bool = True,
        model_path: str = "models/xgb_full.joblib",
        model_long_threshold: float = 0.55,
        kill_switch: bool = False,
        max_trades_per_day: int = 3,
        cooldown_minutes_after_loss: int = 120,
        decision_log_path: str = "logs/paper_validation/decisions.csv",
        fill_log_path: str = "logs/paper_validation/fills.csv",
        daily_snapshot_path: str = "logs/paper_validation/daily_snapshot.csv",
        max_notional_per_order_usd: float = 10000.0,
        max_consecutive_losses: int = 3,
        max_data_staleness_minutes: int = 1440,
    ):
        self.symbol = symbol
        self.is_crypto = self._is_crypto_symbol(symbol)
        if self.is_crypto:
            self.set_market("24/7")
            self.sleeptime = "15M"
        else:
            self.set_market("NASDAQ")
            self.sleeptime = "24H"
        self.cash_at_risk = cash_at_risk
        self.sentiment_probability_threshold = sentiment_probability_threshold
        self.slippage_bps = slippage_bps
        self.commission_per_share = commission_per_share
        self.use_model_signal = use_model_signal
        self.model_path = model_path
        self.model_long_threshold = model_long_threshold
        self.kill_switch = kill_switch
        self.max_trades_per_day = max_trades_per_day
        self.cooldown_minutes_after_loss = cooldown_minutes_after_loss
        self.decision_log_path = Path(decision_log_path)
        self.fill_log_path = Path(fill_log_path)
        self.daily_snapshot_path = Path(daily_snapshot_path)
        self.max_notional_per_order_usd = max_notional_per_order_usd
        self.max_consecutive_losses = max_consecutive_losses
        self.max_data_staleness_minutes = max_data_staleness_minutes
        self._model = None

        limits = RiskLimits(
            max_position_pct=max_position_pct,
            max_gross_leverage=max_gross_leverage,
            allow_short=allow_short,
            daily_loss_limit_pct=daily_loss_limit_pct,
        )
        self.risk_manager = RiskManager(limits)
        self.data_handler = DataHandler(source="alpaca")
        self._day_anchor_date: date | None = None
        self._day_anchor_equity: float | None = None
        self._last_snapshot_date: date | None = None
        self._trades_today = 0
        self._cooldown_until = None
        self._pending_trade_equity_anchor = None
        self._consecutive_losses = 0
        self._last_features_timestamp = None

        self._ensure_log_files()

    @staticmethod
    def _is_crypto_symbol(symbol: str) -> bool:
        normalized = str(symbol).upper().replace("-", "/")
        if "/" in normalized:
            return True
        return normalized.endswith("USD") and len(normalized) > 3

    def _ensure_csv_file(self, path: Path, headers: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return
        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writeheader()

    def _ensure_log_files(self) -> None:
        self._ensure_csv_file(
            self.decision_log_path,
            [
                "timestamp",
                "symbol",
                "action",
                "action_source",
                "model_prob_up",
                "sentiment_probability",
                "sentiment_label",
                "quantity",
                "portfolio_value",
                "cash",
                "reason",
            ],
        )
        self._ensure_csv_file(
            self.fill_log_path,
            ["timestamp", "symbol", "side", "quantity", "order_id", "portfolio_value", "cash", "notional_usd"],
        )
        self._ensure_csv_file(
            self.daily_snapshot_path,
            ["date", "symbol", "portfolio_value", "cash", "position_qty", "day_pnl"],
        )

    @staticmethod
    def _append_csv(path: Path, row: dict) -> None:
        with path.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=list(row.keys()))
            writer.writerow(row)

    def _current_position_qty(self) -> float:
        try:
            position = self.get_position(self.symbol)
            if position is not None and hasattr(position, "quantity"):
                return float(position.quantity)
        except Exception:
            pass

        try:
            for position in self.get_positions():
                asset_symbol = getattr(position, "symbol", None)
                if asset_symbol == self.symbol and hasattr(position, "quantity"):
                    return float(position.quantity)
        except Exception:
            pass
        return 0.0

    def _get_portfolio_value(self) -> float:
        value = getattr(self, "portfolio_value", None)
        if value is not None:
            return float(value)
        return float(self.get_cash())

    def _reset_day_anchor_if_needed(self) -> None:
        now = self.get_datetime().date()
        if self._day_anchor_date != now:
            self._day_anchor_date = now
            self._day_anchor_equity = self._get_portfolio_value()
            self._trades_today = 0
            self._cooldown_until = None

    def _log_daily_snapshot_once(self) -> None:
        now_date = self.get_datetime().date()
        if self._last_snapshot_date == now_date:
            return
        self._last_snapshot_date = now_date
        anchor = self._day_anchor_equity if self._day_anchor_equity is not None else self._get_portfolio_value()
        current = self._get_portfolio_value()
        self._append_csv(
            self.daily_snapshot_path,
            {
                "date": str(now_date),
                "symbol": self.symbol,
                "portfolio_value": round(current, 6),
                "cash": round(float(self.get_cash()), 6),
                "position_qty": round(self._current_position_qty(), 6),
                "day_pnl": round(current - float(anchor), 6),
            },
        )

    def _get_news_window(self) -> tuple[str, str]:
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime("%Y-%m-%d"), three_days_prior.strftime("%Y-%m-%d")

    def _get_sentiment(self) -> tuple[float, str]:
        today, prior = self._get_news_window()
        headlines = self.data_handler.get_news_headlines(
            symbol=self.symbol,
            start=prior,
            end=today,
        )
        probability, sentiment = estimate_sentiment(headlines)
        return float(probability), str(sentiment)

    def _get_sentiment_features(self) -> tuple[float, int]:
        today, prior = self._get_news_window()
        headlines = self.data_handler.get_news_headlines(
            symbol=self.symbol,
            start=prior,
            end=today,
        )
        if not headlines:
            return 0.0, 0
        scores = score_headlines(headlines)
        if not scores:
            return 0.0, 0
        return float(sum(scores) / len(scores)), int(len(scores))

    def _load_model_if_needed(self):
        if not self.use_model_signal:
            return None
        if self._model is not None:
            return self._model
        model_file = Path(self.model_path)
        if not model_file.exists():
            LOGGER.warning("Model not found at %s; falling back to sentiment rule.", self.model_path)
            return None
        self._model = joblib.load(model_file)
        LOGGER.info("Loaded model signal from %s", self.model_path)
        return self._model

    def _get_recent_features(self) -> pd.DataFrame | None:
        now = self.get_datetime()
        start = (now - Timedelta(days=45)).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        bars = self.data_handler.get_bars(
            symbol=self.symbol,
            timeframe="1Day",
            start=start,
            end=end,
        )
        if bars.empty or "close" not in bars.columns:
            return None

        bars = bars.copy()
        bars["timestamp"] = pd.to_datetime(bars["timestamp"], utc=True, errors="coerce")
        bars = bars.dropna(subset=["timestamp"]).sort_values("timestamp")
        if len(bars) < 25:
            return None

        bars["ret_1"] = bars["close"].pct_change()
        bars["sma_20"] = bars["close"].rolling(20).mean()
        bars["ema_20"] = bars["close"].ewm(span=20, adjust=False).mean()

        delta = bars["close"].diff()
        gains = delta.clip(lower=0.0)
        losses = -delta.clip(upper=0.0)
        avg_gain = gains.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
        avg_loss = losses.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0.0, 1e-12)
        bars["rsi_14"] = 100.0 - (100.0 / (1.0 + rs))

        vol_mean = bars["volume"].rolling(20).mean()
        vol_std = bars["volume"].rolling(20).std()
        bars["volume_z20"] = (bars["volume"] - vol_mean) / vol_std.replace(0.0, 1e-12)

        sentiment_mean, sentiment_count = self._get_sentiment_features()
        latest = bars.iloc[-1]
        self._last_features_timestamp = latest["timestamp"]
        row = pd.DataFrame(
            [
                {
                    "symbol": self.symbol,
                    "ret_1": latest.get("ret_1", float("nan")),
                    "sma_20": latest.get("sma_20", float("nan")),
                    "ema_20": latest.get("ema_20", float("nan")),
                    "rsi_14": latest.get("rsi_14", float("nan")),
                    "volume_z20": latest.get("volume_z20", float("nan")),
                    "sentiment_mean": sentiment_mean,
                    "sentiment_count": sentiment_count,
                }
            ]
        )
        return row

    def _is_market_data_stale(self) -> bool:
        if self._last_features_timestamp is None:
            return False
        now = pd.to_datetime(self.get_datetime(), utc=True, errors="coerce")
        feature_ts = pd.to_datetime(self._last_features_timestamp, utc=True, errors="coerce")
        if pd.isna(now) or pd.isna(feature_ts):
            return False
        age_minutes = (now - feature_ts).total_seconds() / 60.0
        return age_minutes > float(self.max_data_staleness_minutes)

    def _get_model_signal(self) -> tuple[str | None, float | None]:
        model = self._load_model_if_needed()
        if model is None:
            return None, None
        features = self._get_recent_features()
        if features is None:
            return None, None

        if hasattr(model, "predict_proba"):
            prob_up = float(model.predict_proba(features)[0, 1])
        else:
            pred = int(model.predict(features)[0])
            prob_up = float(pred)

        long_threshold = self.model_long_threshold
        short_threshold = 1.0 - long_threshold
        if prob_up >= long_threshold:
            return "buy", prob_up
        if prob_up <= short_threshold:
            return "sell", prob_up
        return None, prob_up

    def _effective_price(self, side: str, last_price: float) -> float:
        slippage = self.slippage_bps / 10000.0
        if side == "buy":
            return last_price * (1.0 + slippage)
        return last_price * (1.0 - slippage)

    def _submit_sized_order(self, side: str) -> dict:
        last_price = self.get_last_price(self.symbol)
        if not last_price or last_price <= 0:
            return {"executed": False, "reason": "invalid_last_price", "quantity": 0, "order_id": ""}

        current_qty = self._current_position_qty()
        portfolio_value = self._get_portfolio_value()
        cash = float(self.get_cash())

        max_position_qty = self.risk_manager.max_position_quantity(portfolio_value, last_price)
        if max_position_qty <= 0:
            return {"executed": False, "reason": "max_position_zero", "quantity": 0, "order_id": ""}

        if side == "buy":
            effective_price = self._effective_price(side, last_price)
            budget_qty = floor((cash * self.cash_at_risk) / max(effective_price, 0.01))
            target_qty = max(0, min(max_position_qty, budget_qty))
            delta_qty = max(0, target_qty - floor(current_qty))
            order_side = "buy"
        else:
            if not self.risk_manager.limits.allow_short:
                if current_qty <= 0:
                    return {
                        "executed": False,
                        "reason": "no_long_position_to_sell",
                        "quantity": 0,
                        "order_id": "",
                    }
                delta_qty = floor(current_qty)
                order_side = "sell"
            else:
                target_qty = -max_position_qty
                delta_qty = max(0, floor(current_qty - target_qty))
                order_side = "sell"

        if delta_qty <= 0:
            return {"executed": False, "reason": "delta_qty_zero", "quantity": 0, "order_id": ""}

        order_notional = abs(float(delta_qty) * float(last_price))
        if order_notional > float(self.max_notional_per_order_usd):
            capped_qty = floor(float(self.max_notional_per_order_usd) / max(float(last_price), 0.01))
            if capped_qty <= 0:
                return {"executed": False, "reason": "max_notional_blocked", "quantity": 0, "order_id": ""}
            delta_qty = min(delta_qty, capped_qty)
            order_notional = abs(float(delta_qty) * float(last_price))

        projected_leverage = self.risk_manager.estimate_gross_leverage(
            current_qty=current_qty,
            proposed_delta_qty=delta_qty if order_side == "buy" else -delta_qty,
            price=last_price,
            portfolio_value=portfolio_value,
        )
        if projected_leverage > self.risk_manager.limits.max_gross_leverage:
            return {"executed": False, "reason": "gross_leverage_blocked", "quantity": 0, "order_id": ""}

        order = self.create_order(self.symbol, int(delta_qty), order_side, type="market")
        submission = self.submit_order(order)
        order_id = getattr(submission, "identifier", "") or getattr(order, "identifier", "")
        self._trades_today += 1
        self._pending_trade_equity_anchor = portfolio_value
        self._append_csv(
            self.fill_log_path,
            {
                "timestamp": self.get_datetime().isoformat(),
                "symbol": self.symbol,
                "side": order_side,
                "quantity": int(delta_qty),
                "order_id": order_id,
                "portfolio_value": round(portfolio_value, 6),
                "cash": round(float(self.get_cash()), 6),
                "notional_usd": round(order_notional, 6),
            },
        )
        return {"executed": True, "reason": "submitted", "quantity": int(delta_qty), "order_id": order_id}

    def _set_cooldown_if_recent_trade_lost(self) -> None:
        if self._pending_trade_equity_anchor is None:
            return
        current = self._get_portfolio_value()
        if current < float(self._pending_trade_equity_anchor):
            self._consecutive_losses += 1
            self._cooldown_until = self.get_datetime() + Timedelta(minutes=self.cooldown_minutes_after_loss)
        else:
            self._consecutive_losses = 0
        self._pending_trade_equity_anchor = None

    def _log_decision(
        self,
        action: str,
        action_source: str,
        model_prob_up: float | None,
        sentiment_probability: float | None,
        sentiment_label: str | None,
        quantity: int,
        reason: str,
    ) -> None:
        self._append_csv(
            self.decision_log_path,
            {
                "timestamp": self.get_datetime().isoformat(),
                "symbol": self.symbol,
                "action": action,
                "action_source": action_source,
                "model_prob_up": "" if model_prob_up is None else round(model_prob_up, 6),
                "sentiment_probability": ""
                if sentiment_probability is None
                else round(float(sentiment_probability), 6),
                "sentiment_label": "" if sentiment_label is None else sentiment_label,
                "quantity": quantity,
                "portfolio_value": round(self._get_portfolio_value(), 6),
                "cash": round(float(self.get_cash()), 6),
                "reason": reason,
            },
        )

    def on_trading_iteration(self):
        self._reset_day_anchor_if_needed()
        self._log_daily_snapshot_once()
        self._set_cooldown_if_recent_trade_lost()

        if self.kill_switch:
            self.sell_all()
            self._log_decision("flat", "guardrail", None, None, None, 0, "kill_switch_enabled")
            return

        anchor = self._day_anchor_equity
        if anchor is not None and self.risk_manager.breaches_daily_loss(
            day_start_equity=anchor,
            current_equity=self._get_portfolio_value(),
        ):
            self.sell_all()
            self._log_decision("flat", "guardrail", None, None, None, 0, "daily_loss_limit_breached")
            return

        if self._consecutive_losses >= int(self.max_consecutive_losses):
            self.sell_all()
            self._log_decision(
                "flat",
                "guardrail",
                None,
                None,
                None,
                0,
                f"max_consecutive_losses_reached_{self._consecutive_losses}",
            )
            return

        if self._cooldown_until is not None and self.get_datetime() < self._cooldown_until:
            self._log_decision("hold", "guardrail", None, None, None, 0, "cooldown_active")
            return

        if self._trades_today >= self.max_trades_per_day:
            self._log_decision("hold", "guardrail", None, None, None, 0, "max_trades_per_day_reached")
            return

        probability, sentiment = self._get_sentiment()
        model_signal, model_prob_up = self._get_model_signal()
        if self._is_market_data_stale():
            self._log_decision("hold", "guardrail", model_prob_up, probability, sentiment, 0, "stale_market_data")
            return
        if model_signal is not None:
            result = self._submit_sized_order(model_signal)
            self._log_decision(
                model_signal if result["executed"] else "hold",
                "model",
                model_prob_up,
                probability,
                sentiment,
                int(result.get("quantity", 0)),
                result.get("reason", ""),
            )
            return

        if probability >= self.sentiment_probability_threshold:
            if sentiment == "positive":
                result = self._submit_sized_order("buy")
                self._log_decision(
                    "buy" if result["executed"] else "hold",
                    "sentiment",
                    model_prob_up,
                    probability,
                    sentiment,
                    int(result.get("quantity", 0)),
                    result.get("reason", ""),
                )
            elif sentiment == "negative":
                result = self._submit_sized_order("sell")
                self._log_decision(
                    "sell" if result["executed"] else "hold",
                    "sentiment",
                    model_prob_up,
                    probability,
                    sentiment,
                    int(result.get("quantity", 0)),
                    result.get("reason", ""),
                )
            else:
                self._log_decision(
                    "hold",
                    "sentiment",
                    model_prob_up,
                    probability,
                    sentiment,
                    0,
                    "sentiment_neutral",
                )
        else:
            self._log_decision(
                "hold",
                "sentiment",
                model_prob_up,
                probability,
                sentiment,
                0,
                "sentiment_probability_below_threshold",
            )

    def _dump_benchmark_stats(self):
        # Disable Lumibot's Yahoo benchmark fetch to avoid rate-limit failures
        # in environments where yfinance access is unstable.
        self._benchmark_returns_df = None
