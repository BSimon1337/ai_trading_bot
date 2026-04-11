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
    if model_signal in {"buy", "sell"}:
        return SignalDecision(action=model_signal, source="model", reason="model_signal")

    if sentiment_probability < sentiment_probability_threshold:
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
