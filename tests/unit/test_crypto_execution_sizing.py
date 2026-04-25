from __future__ import annotations

from decimal import Decimal

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
    strategy.fill_log_path = None

    observed: dict[str, object] = {}
    strategy.get_last_price = lambda asset, quote=None: observed.update(asset=asset, quote=quote) or 100_000.0
    strategy.get_cash = lambda: 100.0
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy.get_datetime = lambda: type("FakeDate", (), {"isoformat": lambda self: "2026-04-12T00:00:00"})()
    strategy._append_csv = lambda path, row: observed.update(fill_row=row)
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
    strategy.fill_log_path = None

    observed: dict[str, object] = {}
    strategy.get_last_price = lambda asset, quote=None: 100_000.0
    strategy.get_cash = lambda: 100.0
    strategy._get_portfolio_value = lambda: 100.0
    strategy._current_position_qty = lambda: 0.0
    strategy._append_csv = lambda path, row: observed.update(fill_row=row)
    strategy.create_order = lambda *args, **kwargs: type("Order", (), {"identifier": "order-1", "status": "new"})()
    strategy.submit_order = lambda order: type("Submission", (), {"identifier": "submission-1", "status": "error"})()

    result = strategy._submit_sized_order("buy")

    assert result["executed"] is False
    assert result["reason"] == "broker_error"
    assert "fill_row" not in observed
