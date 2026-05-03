from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd

from tradingbot.strategy.lumibot_strategy import SentimentMLStrategy


def test_crypto_order_uses_fractional_base_quote_assets():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "BTC/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.cash_at_risk = 0.2
    strategy.slippage_bps = 0.0
    strategy.max_notional_per_order_usd = 25.0
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False, "max_gross_leverage": 1.0})(),
            "max_position_quantity": lambda self, portfolio_value, last_price, allow_fractional=False: 25.0 / last_price,
            "estimate_gross_leverage": lambda self, current_qty, proposed_delta_qty, price, portfolio_value: 0.25,
        },
    )()
    strategy._trades_today = 0
    strategy._pending_trade_equity_anchor = None
    strategy._deferred_crypto_order_qty = 0.0
    strategy._deferred_crypto_order_side = None
    strategy.fill_log_path = None

    observed: dict[str, object] = {}
    strategy.get_last_price = lambda asset, quote=None: observed.update(asset=asset, quote=quote) or 100_000.0
    strategy.get_cash = lambda: 100.0
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy.get_datetime = lambda: type("FakeDate", (), {"isoformat": lambda self: "2026-04-12T00:00:00"})()
    strategy._append_csv = lambda path, row, headers=None: observed.update(fill_row=row)
    strategy.create_order = lambda asset, qty, side, **kwargs: observed.update(order=(asset, qty, side, kwargs)) or type("Order", (), {"identifier": "order-1"})()
    strategy.submit_order = lambda order: type("Submission", (), {"identifier": "submission-1"})()

    result = strategy._submit_sized_order("buy")

    assert result["executed"] is True
    assert observed["asset"].symbol == "BTC"
    assert observed["quote"].symbol == "USD"
    assert observed["order"][1] == Decimal("0.0002")
    assert observed["order"][3]["quote"].symbol == "USD"
    assert observed["order"][3]["order_type"] == "market"


def test_crypto_order_rejection_is_not_logged_as_submitted():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "BTC/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.cash_at_risk = 0.2
    strategy.slippage_bps = 0.0
    strategy.max_notional_per_order_usd = 25.0
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False, "max_gross_leverage": 1.0})(),
            "max_position_quantity": lambda self, portfolio_value, last_price, allow_fractional=False: 25.0 / last_price,
            "estimate_gross_leverage": lambda self, current_qty, proposed_delta_qty, price, portfolio_value: 0.25,
        },
    )()
    strategy._trades_today = 0
    strategy._pending_trade_equity_anchor = None
    strategy._deferred_crypto_order_qty = 0.0
    strategy._deferred_crypto_order_side = None
    strategy.fill_log_path = None

    observed: dict[str, object] = {}
    strategy.get_last_price = lambda asset, quote=None: 100_000.0
    strategy.get_cash = lambda: 100.0
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy._append_csv = lambda path, row, headers=None: observed.update(fill_row=row)
    strategy.create_order = lambda *args, **kwargs: type("Order", (), {"identifier": "order-1", "status": "new"})()
    strategy.submit_order = lambda order: type("Submission", (), {"identifier": "submission-1", "status": "error"})()

    result = strategy._submit_sized_order("buy")

    assert result["executed"] is False
    assert result["reason"] == "broker_error"
    assert "fill_row" not in observed


def test_crypto_order_rejection_includes_broker_message():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "DOGE/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.cash_at_risk = 0.2
    strategy.slippage_bps = 0.0
    strategy.max_notional_per_order_usd = 25.0
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False, "max_gross_leverage": 1.0})(),
            "max_position_quantity": lambda self, portfolio_value, last_price, allow_fractional=False: 25.0 / last_price,
            "estimate_gross_leverage": lambda self, current_qty, proposed_delta_qty, price, portfolio_value: 0.25,
        },
    )()
    strategy._trades_today = 0
    strategy._pending_trade_equity_anchor = None
    strategy._deferred_crypto_order_qty = 0.0
    strategy._deferred_crypto_order_side = None
    strategy.fill_log_path = None

    strategy.get_last_price = lambda asset, quote=None: 0.11
    strategy.get_cash = lambda: 40.0
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 92.21761991
    strategy.create_order = lambda *args, **kwargs: type("Order", (), {"identifier": "order-1", "status": "new"})()
    strategy.submit_order = lambda order: type(
        "Submission",
        (),
        {"identifier": "submission-1", "status": "error", "message": "insufficient qty available"},
    )()

    result = strategy._submit_sized_order("sell")

    assert result["executed"] is False
    assert result["reason"] == "broker_error:insufficient qty available"


def test_crypto_order_below_min_notional_is_skipped_before_broker_submission():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "BTC/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.cash_at_risk = 0.2
    strategy.slippage_bps = 0.0
    strategy.max_notional_per_order_usd = 25.0
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False, "max_gross_leverage": 1.0})(),
            "max_position_quantity": lambda self, portfolio_value, last_price, allow_fractional=False: 25.0 / last_price,
            "estimate_gross_leverage": lambda self, current_qty, proposed_delta_qty, price, portfolio_value: 0.25,
        },
    )()
    strategy._trades_today = 0
    strategy._pending_trade_equity_anchor = None
    strategy._deferred_crypto_order_qty = 0.0
    strategy._deferred_crypto_order_side = None
    strategy.fill_log_path = None

    observed: dict[str, object] = {"create_order_called": False}
    strategy.get_last_price = lambda asset, quote=None: 80_000.0
    strategy.get_cash = lambda: 0.10
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy.create_order = lambda *args, **kwargs: observed.update(create_order_called=True)
    strategy.submit_order = lambda order: observed.update(submit_order_called=True)

    result = strategy._submit_sized_order("buy")

    assert result["executed"] is False
    assert result["reason"] == "crypto_order_below_min_notional_accumulating"
    assert observed["create_order_called"] is False
    assert strategy._deferred_crypto_order_qty > 0
    assert strategy._deferred_crypto_order_side == "buy"


def test_crypto_order_accumulates_until_minimum_notional_then_submits():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "BTC/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.cash_at_risk = 1.0
    strategy.slippage_bps = 0.0
    strategy.max_notional_per_order_usd = 25.0
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False, "max_gross_leverage": 1.0})(),
            "max_position_quantity": lambda self, portfolio_value, last_price, allow_fractional=False: 25.0 / last_price,
            "estimate_gross_leverage": lambda self, current_qty, proposed_delta_qty, price, portfolio_value: 0.25,
        },
    )()
    strategy._trades_today = 0
    strategy._pending_trade_equity_anchor = None
    strategy._deferred_crypto_order_qty = 0.0
    strategy._deferred_crypto_order_side = None
    strategy.fill_log_path = None

    observed: dict[str, object] = {}
    cash_state = {"value": 0.50}
    strategy.get_last_price = lambda asset, quote=None: 80_000.0
    strategy.get_cash = lambda: cash_state["value"]
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy.get_datetime = lambda: type("FakeDate", (), {"isoformat": lambda self: "2026-04-12T00:00:00"})()
    strategy._append_csv = lambda path, row, headers=None: observed.update(fill_row=row)
    strategy.create_order = lambda asset, qty, side, **kwargs: observed.update(order=(asset, qty, side, kwargs)) or type("Order", (), {"identifier": "order-1"})()
    strategy.submit_order = lambda order: type("Submission", (), {"identifier": "submission-1"})()

    first = strategy._submit_sized_order("buy")
    cash_state["value"] = 0.60
    second = strategy._submit_sized_order("buy")

    assert first["executed"] is False
    assert first["reason"] == "crypto_order_below_min_notional_accumulating"
    assert second["executed"] is True
    assert observed["order"][1] == Decimal("0.00001375")
    assert strategy._deferred_crypto_order_qty == 0.0
    assert strategy._deferred_crypto_order_side is None


def test_crypto_decision_logging_keeps_fractional_submitted_quantity():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "BTC/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.kill_switch = False
    strategy._trades_today = 0
    strategy.max_trades_per_day = 50
    strategy._cooldown_until = None
    strategy._consecutive_losses = 0
    strategy.max_consecutive_losses = 3
    strategy.sentiment_probability_threshold = 0.7
    strategy._day_anchor_equity = 100.0
    strategy.decision_log_path = Path("logs/test/decisions.csv")
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False})(),
            "breaches_daily_loss": lambda self, day_start_equity, current_equity: False,
        },
    )()

    observed: dict[str, object] = {}
    strategy._reset_day_anchor_if_needed = lambda: None
    strategy._log_snapshot_if_due = lambda: None
    strategy._set_cooldown_if_recent_trade_lost = lambda: None
    strategy._get_portfolio_value = lambda: 100.0
    strategy.get_cash = lambda: 80.0
    strategy.get_datetime = lambda: pd.Timestamp("2026-04-25T17:00:00Z")
    strategy._get_sentiment = lambda: (1.0, "neutral")
    strategy.data_handler = type("FakeDataHandler", (), {"last_news_source": "external"})()
    strategy._get_model_signal = lambda: ("buy", 0.75)
    strategy._is_market_data_stale = lambda: False
    strategy._submit_sized_order = lambda side: {
        "executed": True,
        "reason": "submitted",
        "quantity": 0.00018074,
        "order_id": "order-1",
    }
    strategy._append_csv = lambda path, row, headers=None: observed.update(decision_row=row)

    strategy.on_trading_iteration()

    assert observed["decision_row"]["action"] == "buy"
    assert observed["decision_row"]["result"] == "submitted"
    assert observed["decision_row"]["quantity"] == 0.00018074


def test_crypto_daily_feature_staleness_allows_previous_day_boundary():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.is_crypto = True
    strategy.max_data_staleness_minutes = 1440
    strategy._last_features_timestamp = pd.Timestamp("2026-04-30T00:00:00Z")
    strategy.get_datetime = lambda: pd.Timestamp("2026-05-01T00:12:00Z")

    assert strategy._is_market_data_stale() is False


def test_crypto_daily_feature_staleness_still_blocks_truly_old_data():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.is_crypto = True
    strategy.max_data_staleness_minutes = 1440
    strategy._last_features_timestamp = pd.Timestamp("2026-04-28T00:00:00Z")
    strategy.get_datetime = lambda: pd.Timestamp("2026-05-01T00:12:00Z")

    assert strategy._is_market_data_stale() is True


def test_stock_daily_feature_staleness_allows_prior_trading_day_boundary():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.is_crypto = False
    strategy.max_data_staleness_minutes = 1440
    strategy._last_features_timestamp = pd.Timestamp("2026-04-30T00:00:00Z")
    strategy.get_datetime = lambda: pd.Timestamp("2026-05-01T00:12:00Z")

    assert strategy._is_market_data_stale() is False


def test_stock_daily_feature_staleness_still_blocks_truly_old_data():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.is_crypto = False
    strategy.max_data_staleness_minutes = 1440
    strategy._last_features_timestamp = pd.Timestamp("2026-04-24T00:00:00Z")
    strategy.get_datetime = lambda: pd.Timestamp("2026-05-01T00:12:00Z")

    assert strategy._is_market_data_stale() is True


def test_on_filled_order_logs_actual_crypto_sell_fill():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "ETH/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.fill_log_path = Path("logs/test/fills.csv")

    observed: dict[str, object] = {}
    strategy.get_datetime = lambda: pd.Timestamp("2026-04-26T13:43:00Z")
    strategy.get_cash = lambda: 99.24
    strategy._get_portfolio_value = lambda: 99.24
    strategy._append_csv = lambda path, row, headers=None: observed.update(fill_row=row)

    order = type("Order", (), {"side": "sell", "identifier": "order-eth-flat"})()

    strategy.on_filled_order(None, order, 2310.5, 0.004295, 1.0)

    assert observed["fill_row"]["side"] == "sell"
    assert observed["fill_row"]["quantity"] == 0.004295
    assert observed["fill_row"]["order_id"] == "order-eth-flat"
    assert observed["fill_row"]["result"] == "filled"
    assert observed["fill_row"]["notional_usd"] == round(2310.5 * 0.004295, 6)


def test_guardrail_flat_logs_submitted_when_position_exists():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "ETH/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.kill_switch = False
    strategy._trades_today = 0
    strategy.max_trades_per_day = 50
    strategy._cooldown_until = None
    strategy._consecutive_losses = 3
    strategy._loss_lockout_date = None
    strategy.max_consecutive_losses = 3
    strategy._day_anchor_equity = 100.0
    strategy.decision_log_path = Path("logs/test/decisions.csv")
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False})(),
            "breaches_daily_loss": lambda self, day_start_equity, current_equity: False,
        },
    )()

    observed: dict[str, object] = {}
    strategy._reset_day_anchor_if_needed = lambda: None
    strategy._log_snapshot_if_due = lambda: None
    strategy._set_cooldown_if_recent_trade_lost = lambda: None
    strategy._current_position_qty = lambda: 0.004295
    strategy.sell_all = lambda: observed.update(sell_all_called=True)
    strategy._get_portfolio_value = lambda: 99.24
    strategy.get_cash = lambda: 99.24
    strategy.get_datetime = lambda: pd.Timestamp("2026-04-26T13:43:00Z")
    strategy._append_csv = lambda path, row, headers=None: observed.update(decision_row=row)

    strategy.on_trading_iteration()

    assert observed["sell_all_called"] is True
    assert observed["decision_row"]["action"] == "flat"
    assert observed["decision_row"]["quantity"] == 0.004295
    assert observed["decision_row"]["result"] == "submitted"
    assert observed["decision_row"]["reason"] == "max_consecutive_losses_reached_3"


def test_loss_lockout_holds_for_rest_of_day_without_repeated_sell_all():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy.symbol = "ETH/USD"
    strategy.mode = "live"
    strategy.is_crypto = True
    strategy.asset_class = "crypto"
    strategy.kill_switch = False
    strategy._trades_today = 0
    strategy.max_trades_per_day = 50
    strategy._cooldown_until = None
    strategy._consecutive_losses = 3
    strategy._loss_lockout_date = pd.Timestamp("2026-04-26T00:00:00Z").date()
    strategy.max_consecutive_losses = 3
    strategy._day_anchor_equity = 100.0
    strategy.decision_log_path = Path("logs/test/decisions.csv")
    strategy.risk_manager = type(
        "FakeRiskManager",
        (),
        {
            "limits": type("FakeLimits", (), {"allow_short": False})(),
            "breaches_daily_loss": lambda self, day_start_equity, current_equity: False,
        },
    )()

    observed: dict[str, object] = {"sell_all_called": False}
    strategy._reset_day_anchor_if_needed = lambda: None
    strategy._log_snapshot_if_due = lambda: None
    strategy._set_cooldown_if_recent_trade_lost = lambda: None
    strategy.sell_all = lambda: observed.update(sell_all_called=True)
    strategy._get_portfolio_value = lambda: 99.24
    strategy.get_cash = lambda: 99.24
    strategy.get_datetime = lambda: pd.Timestamp("2026-04-26T18:00:00Z")
    strategy._append_csv = lambda path, row, headers=None: observed.update(decision_row=row)

    strategy.on_trading_iteration()

    assert observed["sell_all_called"] is False
    assert observed["decision_row"]["action"] == "hold"
    assert observed["decision_row"]["result"] == "skipped"
    assert observed["decision_row"]["reason"] == "max_consecutive_losses_lockout_until_next_day_3"


def test_day_anchor_reset_clears_consecutive_loss_lockout():
    strategy = SentimentMLStrategy.__new__(SentimentMLStrategy)
    strategy._day_anchor_date = pd.Timestamp("2026-04-26T00:00:00Z").date()
    strategy._day_anchor_equity = 95.0
    strategy._trades_today = 4
    strategy._cooldown_until = pd.Timestamp("2026-04-26T12:00:00Z")
    strategy._consecutive_losses = 3
    strategy._loss_lockout_date = pd.Timestamp("2026-04-26T00:00:00Z").date()
    strategy._get_portfolio_value = lambda: 101.0
    strategy.get_datetime = lambda: pd.Timestamp("2026-04-27T00:05:00Z")

    strategy._reset_day_anchor_if_needed()

    assert strategy._day_anchor_date == pd.Timestamp("2026-04-27T00:05:00Z").date()
    assert strategy._day_anchor_equity == 101.0
    assert strategy._trades_today == 0
    assert strategy._cooldown_until is None
    assert strategy._consecutive_losses == 0
    assert strategy._loss_lockout_date is None
