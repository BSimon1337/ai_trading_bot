from __future__ import annotations

from tradingbot.strategy import lumibot_strategy


def test_model_load_failure_falls_back_to_sentiment(monkeypatch, tmp_path):
    model_file = tmp_path / "model.joblib"
    model_file.write_bytes(b"not a real model")

    strategy = lumibot_strategy.SentimentMLStrategy.__new__(lumibot_strategy.SentimentMLStrategy)
    strategy.use_model_signal = True
    strategy._model = None
    strategy._model_load_failed = False
    strategy.model_path = str(model_file)

    monkeypatch.setattr(
        lumibot_strategy.joblib,
        "load",
        lambda path: (_ for _ in ()).throw(ModuleNotFoundError("sklearn")),
    )

    assert strategy._load_model_if_needed() is None
    assert strategy._model is None
    assert strategy._model_load_failed is True
