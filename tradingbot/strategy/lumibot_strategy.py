from __future__ import annotations

import csv
import json
import logging
from datetime import date
from decimal import Decimal
from math import floor
from pathlib import Path

import joblib
import pandas as pd
from lumibot.entities import Asset
from lumibot.strategies.strategy import Strategy
from pandas import Timedelta

from tradingbot.data.news import DataHandler
from tradingbot.execution.logging import DECISION_HEADERS, FILL_HEADERS, SNAPSHOT_HEADERS
from tradingbot.risk.sizing import RiskLimits, RiskManager
from tradingbot.sentiment.scoring import estimate_sentiment, score_headlines
from tradingbot.strategy.signals import choose_trade_action

LOGGER = logging.getLogger(__name__)

MIN_CRYPTO_ORDER_NOTIONAL_USD = 1.0


class SentimentMLStrategy(Strategy):
    def initialize(
        self,
        symbol: str = "SPY",
        asset_class: str | None = None,
        mode: str = "paper",
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
        offline_news_enabled: bool = False,
        offline_news_dir: str = "data/offline_news",
    ):
        self.symbol = symbol
        self.asset_class = asset_class or ("crypto" if self._is_crypto_symbol(symbol) else "stock")
        self.mode = mode
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
        self.offline_news_enabled = offline_news_enabled
        self.offline_news_dir = offline_news_dir
        self._model = None
        self._model_load_failed = False

        limits = RiskLimits(
            max_position_pct=max_position_pct,
            max_gross_leverage=max_gross_leverage,
            allow_short=allow_short,
            daily_loss_limit_pct=daily_loss_limit_pct,
        )
        self.risk_manager = RiskManager(limits)
        self.data_handler = DataHandler(
            source="alpaca",
            offline_news_enabled=offline_news_enabled,
            offline_news_dir=offline_news_dir,
        )
        self._day_anchor_date: date | None = None
        self._day_anchor_equity: float | None = None
        self._last_snapshot_date: date | None = None
        self._last_snapshot_timestamp = None
        self._trades_today = 0
        self._cooldown_until = None
        self._pending_trade_equity_anchor = None
        self._consecutive_losses = 0
        self._last_features_timestamp = None
        self._deferred_crypto_order_qty = 0.0
        self._deferred_crypto_order_side: str | None = None

        self._ensure_log_files()

    @staticmethod
    def _is_crypto_symbol(symbol: str) -> bool:
        normalized = str(symbol).upper().replace("-", "/")
        if "/" in normalized:
            return True
        return normalized.endswith("USD") and len(normalized) > 3

    @staticmethod
    def _split_crypto_symbol(symbol: str) -> tuple[str, str]:
        normalized = str(symbol).upper().replace("-", "/")
        if "/" in normalized:
            base, quote = normalized.split("/", 1)
            return base, quote
        if normalized.endswith("USD") and len(normalized) > 3:
            return normalized[:-3], "USD"
        return normalized, "USD"

    def _trade_asset(self):
        if not self.is_crypto:
            return self.symbol
        base, _ = self._split_crypto_symbol(self.symbol)
        return Asset(symbol=base, asset_type=Asset.AssetType.CRYPTO)

    def _trade_quote_asset(self):
        if not self.is_crypto:
            return None
        _, quote = self._split_crypto_symbol(self.symbol)
        asset_type = Asset.AssetType.FOREX if quote == "USD" else Asset.AssetType.CRYPTO
        return Asset(symbol=quote, asset_type=asset_type)

    @staticmethod
    def _format_order_quantity(quantity: float, allow_fractional: bool):
        if allow_fractional:
            normalized = f"{max(0.0, float(quantity)):.8f}".rstrip("0").rstrip(".")
            return Decimal(normalized)
        return int(quantity)

    def _ensure_csv_file(self, path: Path, headers: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            with path.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.DictWriter(fp, fieldnames=headers)
                writer.writeheader()
            return

        with path.open("r", newline="", encoding="utf-8") as fp:
            reader = csv.DictReader(fp)
            existing_headers = reader.fieldnames or []
            if existing_headers == headers:
                return
            rows = list(reader)

        with path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({header: row.get(header, "") for header in headers})

    def _ensure_log_files(self) -> None:
        self._ensure_csv_file(
            self.decision_log_path,
            DECISION_HEADERS,
        )
        self._ensure_csv_file(self.fill_log_path, FILL_HEADERS)
        self._ensure_csv_file(self.daily_snapshot_path, SNAPSHOT_HEADERS)

    @staticmethod
    def _append_csv(path: Path, row: dict, headers: list[str]) -> None:
        with path.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writerow({header: row.get(header, "") for header in headers})

    def _current_position_qty(self) -> float:
        trade_asset = self._trade_asset()
        try:
            position = self.get_position(trade_asset)
            if position is not None and hasattr(position, "quantity"):
                return float(position.quantity)
        except Exception:
            pass

        try:
            for position in self.get_positions():
                asset_symbol = getattr(position, "symbol", None)
                asset = getattr(position, "asset", None)
                if asset is not None:
                    asset_symbol = getattr(asset, "symbol", asset_symbol)
                if asset_symbol in {self.symbol, getattr(trade_asset, "symbol", self.symbol)} and hasattr(position, "quantity"):
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

    def _log_snapshot_if_due(self) -> None:
        now = self.get_datetime()
        now_date = now.date()
        if self.is_crypto:
            if self._last_snapshot_timestamp is not None:
                elapsed = pd.to_datetime(now, utc=True, errors="coerce") - pd.to_datetime(
                    self._last_snapshot_timestamp,
                    utc=True,
                    errors="coerce",
                )
                if pd.notna(elapsed) and elapsed < Timedelta(minutes=1):
                    return
        elif self._last_snapshot_date == now_date:
            return
        self._last_snapshot_date = now_date
        self._last_snapshot_timestamp = now
        anchor = self._day_anchor_equity if self._day_anchor_equity is not None else self._get_portfolio_value()
        current = self._get_portfolio_value()
        self._append_csv(
            self.daily_snapshot_path,
            {
                "date": now.isoformat(),
                "mode": self.mode,
                "symbol": self.symbol,
                "portfolio_value": round(current, 6),
                "cash": round(float(self.get_cash()), 6),
                "position_qty": round(self._current_position_qty(), 6),
                "day_pnl": round(current - float(anchor), 6),
            },
            SNAPSHOT_HEADERS,
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

    def _sentiment_runtime_evidence(
        self,
        *,
        sentiment_probability: float | None,
        sentiment_label: str | None,
        sentiment_source: str | None,
    ) -> dict[str, object]:
        headline_preview = list(getattr(self.data_handler, "last_headline_preview", []) or [])
        headline_count = int(getattr(self.data_handler, "last_headline_count", len(headline_preview)) or 0)
        source = str(sentiment_source or "")
        label = str(sentiment_label or "")
        probability = None if sentiment_probability is None else float(sentiment_probability)
        if source == "neutral_fallback":
            availability_state = "neutral_fallback"
        elif source == "local_fixture":
            availability_state = "local_fixture_scored"
        elif source == "external" and headline_count > 0 and label:
            availability_state = "news_scored"
        elif headline_count <= 0:
            availability_state = "no_headlines"
        elif label:
            availability_state = "scored"
        else:
            availability_state = "unavailable"

        return {
            "sentiment_source": source,
            "sentiment_probability": "" if probability is None else round(probability, 6),
            "sentiment_label": label,
            "sentiment_availability_state": availability_state,
            "sentiment_is_fallback": str(source == "neutral_fallback").lower(),
            "sentiment_observed_at": getattr(self.data_handler, "last_news_observed_at", "") or self.get_datetime().isoformat(),
            "headline_count": headline_count,
            "headline_preview": json.dumps(headline_preview, ensure_ascii=True),
            "sentiment_window_start": getattr(self.data_handler, "last_news_window_start", ""),
            "sentiment_window_end": getattr(self.data_handler, "last_news_window_end", ""),
        }

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
        if self._model_load_failed:
            return None
        if self._model is not None:
            return self._model
        model_file = Path(self.model_path)
        if not model_file.exists():
            LOGGER.warning("Model not found at %s; falling back to sentiment rule.", self.model_path)
            self._model_load_failed = True
            return None
        try:
            self._model = joblib.load(model_file)
        except Exception as exc:
            LOGGER.warning(
                "Model load failed at %s; falling back to sentiment rule. Error: %s",
                self.model_path,
                exc,
            )
            self._model_load_failed = True
            return None
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
        trade_asset = self._trade_asset()
        quote_asset = self._trade_quote_asset()
        last_price = self.get_last_price(trade_asset, quote=quote_asset) if self.is_crypto else self.get_last_price(trade_asset)
        if not last_price or last_price <= 0:
            return {"executed": False, "reason": "invalid_last_price", "quantity": 0, "order_id": ""}

        current_qty = self._current_position_qty()
        portfolio_value = self._get_portfolio_value()
        cash = float(self.get_cash())

        max_position_qty = self.risk_manager.max_position_quantity(
            portfolio_value,
            last_price,
            allow_fractional=self.is_crypto,
        )
        if max_position_qty <= 0:
            return {"executed": False, "reason": "max_position_zero", "quantity": 0, "order_id": ""}

        if side == "buy":
            effective_price = self._effective_price(side, last_price)
            raw_budget_qty = (cash * self.cash_at_risk) / max(effective_price, 0.01)
            budget_qty = raw_budget_qty if self.is_crypto else floor(raw_budget_qty)
            target_qty = max(0, min(max_position_qty, budget_qty))
            current_anchor = current_qty if self.is_crypto else floor(current_qty)
            delta_qty = max(0, target_qty - current_anchor)
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
                delta_qty = current_qty if self.is_crypto else floor(current_qty)
                order_side = "sell"
            else:
                target_qty = -max_position_qty
                raw_delta_qty = current_qty - target_qty
                delta_qty = max(0, raw_delta_qty if self.is_crypto else floor(raw_delta_qty))
                order_side = "sell"

        if delta_qty <= 0:
            return {"executed": False, "reason": "delta_qty_zero", "quantity": 0, "order_id": ""}

        if self.is_crypto:
            if self._deferred_crypto_order_side not in {None, side}:
                self._deferred_crypto_order_qty = 0.0
                self._deferred_crypto_order_side = None

            deferred_qty = self._deferred_crypto_order_qty if self._deferred_crypto_order_side == side else 0.0
            if deferred_qty > 0:
                if side == "buy":
                    max_buy_delta = max(0.0, max_position_qty - current_qty)
                    delta_qty = min(max_buy_delta, float(delta_qty) + deferred_qty)
                else:
                    delta_qty = min(float(delta_qty) + deferred_qty, max(0.0, current_qty))

        order_notional = abs(float(delta_qty) * float(last_price))
        if self.is_crypto and order_notional < MIN_CRYPTO_ORDER_NOTIONAL_USD:
            self._deferred_crypto_order_qty = float(delta_qty)
            self._deferred_crypto_order_side = side
            return {
                "executed": False,
                "reason": "crypto_order_below_min_notional_accumulating",
                "quantity": float(delta_qty),
                "order_id": "",
            }
        if order_notional > float(self.max_notional_per_order_usd):
            raw_capped_qty = float(self.max_notional_per_order_usd) / max(float(last_price), 0.01)
            capped_qty = raw_capped_qty if self.is_crypto else floor(raw_capped_qty)
            if capped_qty <= 0:
                return {"executed": False, "reason": "max_notional_blocked", "quantity": 0, "order_id": ""}
            delta_qty = min(delta_qty, capped_qty)
            order_notional = abs(float(delta_qty) * float(last_price))
            if self.is_crypto and order_notional < MIN_CRYPTO_ORDER_NOTIONAL_USD:
                self._deferred_crypto_order_qty = float(delta_qty)
                self._deferred_crypto_order_side = side
                return {
                    "executed": False,
                    "reason": "crypto_order_below_min_notional_accumulating",
                    "quantity": float(delta_qty),
                    "order_id": "",
                }

        projected_leverage = self.risk_manager.estimate_gross_leverage(
            current_qty=current_qty,
            proposed_delta_qty=delta_qty if order_side == "buy" else -delta_qty,
            price=last_price,
            portfolio_value=portfolio_value,
        )
        if projected_leverage > self.risk_manager.limits.max_gross_leverage:
            return {"executed": False, "reason": "gross_leverage_blocked", "quantity": 0, "order_id": ""}

        order_quantity = self._format_order_quantity(delta_qty, allow_fractional=self.is_crypto)
        order = self.create_order(trade_asset, order_quantity, order_side, quote=quote_asset, order_type="market")
        submission = self.submit_order(order)
        order_id = getattr(submission, "identifier", "") or getattr(order, "identifier", "")
        order_status = str(getattr(submission, "status", getattr(order, "status", ""))).lower()
        if any(status in order_status for status in {"error", "reject", "cancel"}):
            return {
                "executed": False,
                "reason": f"broker_{order_status or 'order_not_submitted'}",
                "quantity": float(delta_qty),
                "order_id": order_id,
            }
        if self.is_crypto:
            self._deferred_crypto_order_qty = 0.0
            self._deferred_crypto_order_side = None
        self._trades_today += 1
        self._pending_trade_equity_anchor = portfolio_value
        self._append_csv(
            self.fill_log_path,
            {
                "timestamp": self.get_datetime().isoformat(),
                "mode": self.mode,
                "symbol": self.symbol,
                "asset_class": self.asset_class,
                "side": order_side,
                "quantity": order_quantity,
                "order_id": order_id,
                "portfolio_value": round(portfolio_value, 6),
                "cash": round(float(self.get_cash()), 6),
                "notional_usd": round(order_notional, 6),
                "result": "submitted",
            },
            FILL_HEADERS,
        )
        return {"executed": True, "reason": "submitted", "quantity": float(delta_qty), "order_id": order_id}

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
        sentiment_source: str | None,
        quantity: float,
        reason: str,
        sentiment_evidence: dict[str, object] | None = None,
    ) -> None:
        normalized_quantity: float | int = round(float(quantity), 8)
        if not self.is_crypto:
            normalized_quantity = int(quantity)
        row = {
            "timestamp": self.get_datetime().isoformat(),
            "mode": self.mode,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "action": action,
            "action_source": action_source,
            "model_prob_up": "" if model_prob_up is None else round(model_prob_up, 6),
            "sentiment_source": "" if sentiment_source is None else sentiment_source,
            "sentiment_probability": ""
            if sentiment_probability is None
            else round(float(sentiment_probability), 6),
            "sentiment_label": "" if sentiment_label is None else sentiment_label,
            "sentiment_availability_state": "",
            "sentiment_is_fallback": "",
            "sentiment_observed_at": "",
            "headline_count": "",
            "headline_preview": "",
            "sentiment_window_start": "",
            "sentiment_window_end": "",
            "quantity": normalized_quantity,
            "portfolio_value": round(self._get_portfolio_value(), 6),
            "cash": round(float(self.get_cash()), 6),
            "reason": reason,
            "result": "submitted" if quantity > 0 and action in {"buy", "sell"} else "blocked" if action == "hold" and reason.endswith("blocked") else "skipped",
        }
        if sentiment_evidence:
            row.update(sentiment_evidence)
        self._append_csv(self.decision_log_path, row, DECISION_HEADERS)

    def on_trading_iteration(self):
        self._reset_day_anchor_if_needed()
        self._log_snapshot_if_due()
        self._set_cooldown_if_recent_trade_lost()

        if self.kill_switch:
            self.sell_all()
            self._log_decision("flat", "guardrail", None, None, None, None, 0, "kill_switch_enabled")
            return

        anchor = self._day_anchor_equity
        if anchor is not None and self.risk_manager.breaches_daily_loss(
            day_start_equity=anchor,
            current_equity=self._get_portfolio_value(),
        ):
            self.sell_all()
            self._log_decision("flat", "guardrail", None, None, None, None, 0, "daily_loss_limit_breached")
            return

        if self._consecutive_losses >= int(self.max_consecutive_losses):
            self.sell_all()
            self._log_decision(
                "flat",
                "guardrail",
                None,
                None,
                None,
                None,
                0,
                f"max_consecutive_losses_reached_{self._consecutive_losses}",
            )
            return

        if self._cooldown_until is not None and self.get_datetime() < self._cooldown_until:
            self._log_decision("hold", "guardrail", None, None, None, None, 0, "cooldown_active")
            return

        if self._trades_today >= self.max_trades_per_day:
            self._log_decision("hold", "guardrail", None, None, None, None, 0, "max_trades_per_day_reached")
            return

        probability, sentiment = self._get_sentiment()
        sentiment_source = getattr(self.data_handler, "last_news_source", "external")
        sentiment_evidence = self._sentiment_runtime_evidence(
            sentiment_probability=probability,
            sentiment_label=sentiment,
            sentiment_source=sentiment_source,
        )
        model_signal, model_prob_up = self._get_model_signal()
        if self._is_market_data_stale():
            self._log_decision(
                "hold",
                "guardrail",
                model_prob_up,
                probability,
                sentiment,
                sentiment_source,
                0,
                "stale_market_data",
                sentiment_evidence=sentiment_evidence,
            )
            return
        decision = choose_trade_action(
            model_signal=model_signal,
            sentiment_probability=probability,
            sentiment_label=sentiment,
            sentiment_probability_threshold=self.sentiment_probability_threshold,
        )

        if decision.action in {"buy", "sell"}:
            result = self._submit_sized_order(decision.action)
            self._log_decision(
                decision.action if result["executed"] else "hold",
                decision.source,
                model_prob_up,
                probability,
                sentiment,
                sentiment_source,
                float(result.get("quantity", 0.0)),
                result.get("reason", ""),
                sentiment_evidence=sentiment_evidence,
            )
            return

        self._log_decision(
            "hold",
            decision.source,
            model_prob_up,
            probability,
            sentiment,
            sentiment_source,
            0,
            decision.reason,
            sentiment_evidence=sentiment_evidence,
        )

    def _dump_benchmark_stats(self):
        # Disable Lumibot's Yahoo benchmark fetch to avoid rate-limit failures
        # in environments where yfinance access is unstable.
        self._benchmark_returns_df = None
