from __future__ import annotations

from tradingbot.strategy import lumibot_strategy
from tradingbot.app import preflight
from tradingbot.app.preflight import ReadinessStatus
from tests.conftest import make_bot_config


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


def test_preflight_model_load_warning_for_missing_model(tmp_path):
    config = make_bot_config(model_path=str(tmp_path / "missing.joblib"))

    result = preflight.check_model_loadability(config)

    assert result.status == ReadinessStatus.WARNING
    assert "fall back" in result.message


def test_preflight_model_load_warning_for_unloadable_model(monkeypatch, tmp_path):
    model_file = tmp_path / "model.joblib"
    model_file.write_bytes(b"not a real model")
    config = make_bot_config(model_path=str(model_file))

    monkeypatch.setattr(
        preflight.joblib,
        "load",
        lambda path: (_ for _ in ()).throw(ModuleNotFoundError("sklearn")),
    )

    result = preflight.check_model_loadability(config)

    assert result.status == ReadinessStatus.WARNING
    assert "could not be loaded" in result.message


def test_preflight_model_load_passes_when_model_signal_disabled(tmp_path):
    config = make_bot_config(use_model_signal=False, model_path=str(tmp_path / "missing.joblib"))

    result = preflight.check_model_loadability(config)

    assert result.status == ReadinessStatus.PASS
