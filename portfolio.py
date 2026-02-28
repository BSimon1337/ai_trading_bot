from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class RiskLimits:
    max_position_pct: float
    max_gross_leverage: float
    allow_short: bool
    daily_loss_limit_pct: float


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def max_position_quantity(self, portfolio_value: float, last_price: float) -> int:
        if portfolio_value <= 0 or last_price <= 0:
            return 0
        max_notional = portfolio_value * self.limits.max_position_pct
        return max(0, floor(max_notional / last_price))

    def estimate_gross_leverage(
        self,
        current_qty: float,
        proposed_delta_qty: float,
        price: float,
        portfolio_value: float,
    ) -> float:
        if portfolio_value <= 0 or price <= 0:
            return float("inf")
        projected_qty = current_qty + proposed_delta_qty
        projected_notional = abs(projected_qty * price)
        return projected_notional / portfolio_value

    def breaches_daily_loss(self, day_start_equity: float, current_equity: float) -> bool:
        if day_start_equity <= 0:
            return False
        loss_pct = (day_start_equity - current_equity) / day_start_equity
        return loss_pct >= self.limits.daily_loss_limit_pct
