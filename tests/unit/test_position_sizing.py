from tradingbot.risk.sizing import RiskLimits, RiskManager


def test_max_position_quantity_uses_position_pct():
    manager = RiskManager(
        RiskLimits(
            max_position_pct=0.25,
            max_gross_leverage=1.0,
            allow_short=False,
            daily_loss_limit_pct=0.03,
        )
    )

    assert manager.max_position_quantity(portfolio_value=10_000, last_price=100) == 25


def test_max_position_quantity_respects_order_notional_cap():
    manager = RiskManager(
        RiskLimits(
            max_position_pct=0.50,
            max_gross_leverage=1.0,
            allow_short=False,
            daily_loss_limit_pct=0.03,
            max_notional_per_order_usd=1_000,
        )
    )

    assert manager.max_position_quantity(portfolio_value=10_000, last_price=100) == 10


def test_estimate_gross_leverage_projects_delta():
    manager = RiskManager(
        RiskLimits(
            max_position_pct=0.25,
            max_gross_leverage=1.0,
            allow_short=False,
            daily_loss_limit_pct=0.03,
        )
    )

    assert manager.estimate_gross_leverage(5, 5, 100, 10_000) == 0.1


def test_breaches_daily_loss_at_limit():
    manager = RiskManager(
        RiskLimits(
            max_position_pct=0.25,
            max_gross_leverage=1.0,
            allow_short=False,
            daily_loss_limit_pct=0.03,
        )
    )

    assert manager.breaches_daily_loss(day_start_equity=10_000, current_equity=9_700)
