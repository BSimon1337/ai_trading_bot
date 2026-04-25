from __future__ import annotations

from tradingbot.sentiment import scoring


def test_estimate_sentiment_falls_back_to_neutral_when_finbert_missing(monkeypatch):
    monkeypatch.setattr(
        scoring,
        "_load_finbert",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("torch")),
    )

    probability, sentiment = scoring.estimate_sentiment(["crypto headline"])

    assert probability == 0
    assert sentiment == "neutral"


def test_score_headlines_uses_neutral_fallback_when_finbert_missing(monkeypatch):
    monkeypatch.setattr(
        scoring,
        "_load_finbert",
        lambda: (_ for _ in ()).throw(ModuleNotFoundError("transformers")),
    )

    assert scoring.score_headlines(["crypto headline"]) == [0.0]
