from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalDecision:
    action: str
    source: str
    reason: str


def choose_trade_action(
    *,
    model_signal: str | None,
    sentiment_probability: float,
    sentiment_label: str,
    sentiment_probability_threshold: float,
) -> SignalDecision:
    strong_sentiment = sentiment_probability >= sentiment_probability_threshold

    if model_signal == "buy":
        if strong_sentiment and sentiment_label == "negative":
            return SignalDecision(
                action="hold",
                source="model_with_sentiment_confirmation",
                reason="model_buy_blocked_by_negative_sentiment",
            )
        return SignalDecision(
            action="buy",
            source="model_with_sentiment_confirmation",
            reason="model_buy_confirmed_by_sentiment",
        )

    if model_signal == "sell":
        if strong_sentiment and sentiment_label == "positive":
            return SignalDecision(
                action="hold",
                source="model_with_sentiment_confirmation",
                reason="model_sell_blocked_by_positive_sentiment",
            )
        return SignalDecision(
            action="sell",
            source="model_with_sentiment_confirmation",
            reason="model_sell_confirmed_by_sentiment",
        )

    if not strong_sentiment:
        return SignalDecision(
            action="hold",
            source="sentiment",
            reason="sentiment_probability_below_threshold",
        )

    if sentiment_label == "positive":
        return SignalDecision(action="buy", source="sentiment", reason="sentiment_positive")
    if sentiment_label == "negative":
        return SignalDecision(action="sell", source="sentiment", reason="sentiment_negative")

    return SignalDecision(action="hold", source="sentiment", reason="sentiment_neutral")
