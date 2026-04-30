from tradingbot.strategy.signals import choose_trade_action


def test_model_buy_is_allowed_when_sentiment_is_not_bearish():
    decision = choose_trade_action(
        model_signal="buy",
        sentiment_probability=0.95,
        sentiment_label="neutral",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "buy"
    assert decision.source == "model_with_sentiment_confirmation"
    assert decision.reason == "model_buy_confirmed_by_sentiment"


def test_model_sell_is_allowed_when_sentiment_is_not_bullish():
    decision = choose_trade_action(
        model_signal="sell",
        sentiment_probability=0.95,
        sentiment_label="neutral",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "sell"
    assert decision.source == "model_with_sentiment_confirmation"
    assert decision.reason == "model_sell_confirmed_by_sentiment"


def test_model_buy_is_blocked_by_strong_negative_sentiment():
    decision = choose_trade_action(
        model_signal="buy",
        sentiment_probability=0.95,
        sentiment_label="negative",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "hold"
    assert decision.source == "model_with_sentiment_confirmation"
    assert decision.reason == "model_buy_blocked_by_negative_sentiment"


def test_model_sell_is_blocked_by_strong_positive_sentiment():
    decision = choose_trade_action(
        model_signal="sell",
        sentiment_probability=0.95,
        sentiment_label="positive",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "hold"
    assert decision.source == "model_with_sentiment_confirmation"
    assert decision.reason == "model_sell_blocked_by_positive_sentiment"


def test_model_signal_can_proceed_when_sentiment_confidence_is_weak():
    decision = choose_trade_action(
        model_signal="buy",
        sentiment_probability=0.4,
        sentiment_label="negative",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "buy"
    assert decision.source == "model_with_sentiment_confirmation"


def test_sentiment_below_threshold_holds():
    decision = choose_trade_action(
        model_signal=None,
        sentiment_probability=0.69,
        sentiment_label="positive",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "hold"
    assert decision.reason == "sentiment_probability_below_threshold"


def test_positive_sentiment_generates_buy():
    decision = choose_trade_action(
        model_signal=None,
        sentiment_probability=0.8,
        sentiment_label="positive",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "buy"
    assert decision.source == "sentiment"


def test_negative_sentiment_generates_sell():
    decision = choose_trade_action(
        model_signal=None,
        sentiment_probability=0.8,
        sentiment_label="negative",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "sell"
    assert decision.source == "sentiment"
