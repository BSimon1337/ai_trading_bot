from tradingbot.strategy.signals import choose_trade_action


def test_model_signal_takes_precedence_over_sentiment():
    decision = choose_trade_action(
        model_signal="sell",
        sentiment_probability=0.95,
        sentiment_label="positive",
        sentiment_probability_threshold=0.7,
    )

    assert decision.action == "sell"
    assert decision.source == "model"


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
