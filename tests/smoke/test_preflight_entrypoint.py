from __future__ import annotations

from tradingbot.app import main as app_main
from tradingbot.app import preflight
from tradingbot.app.preflight import ReadinessCheckResult, ReadinessStatus
from tests.conftest import make_bot_config


def _patch_diagnostic_checks(monkeypatch):
    monkeypatch.setattr(
        preflight,
        "_check_required_dependencies",
        lambda: ReadinessCheckResult("required_dependencies", ReadinessStatus.PASS, "ok"),
    )
    monkeypatch.setattr(
        preflight,
        "_check_optional_sentiment_dependencies",
        lambda: ReadinessCheckResult("optional_sentiment_dependencies", ReadinessStatus.PASS, "ok"),
    )
    monkeypatch.setattr(
        preflight,
        "check_model_loadability",
        lambda config: ReadinessCheckResult("model_loadability", ReadinessStatus.PASS, "ok"),
    )


def test_preflight_entrypoint_returns_report_exit_code(monkeypatch, capsys):
    observed: dict[str, object] = {}

    monkeypatch.setattr(app_main, "setup_logging", lambda: None)
    monkeypatch.setattr(app_main, "load_config", lambda: make_bot_config())
    monkeypatch.setattr(preflight, "_check_trading_access", lambda config: ReadinessCheckResult("alpaca_trading_access", ReadinessStatus.PASS, "ok"))
    monkeypatch.setattr(preflight, "_check_market_data_access", lambda config: ReadinessCheckResult("alpaca_market_data_access", ReadinessStatus.PASS, "ok"))
    monkeypatch.setattr(preflight, "_check_news_access", lambda config: ReadinessCheckResult("alpaca_news_access", ReadinessStatus.WARNING, "news unavailable"))
    _patch_diagnostic_checks(monkeypatch)
    monkeypatch.setattr(
        app_main,
        "log_run_event",
        lambda paths, mode, result, reason: observed.update(mode=mode, result=result, reason=reason),
    )

    exit_code = app_main.main(["--mode", "preflight", "--preflight-target", "paper"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Preflight readiness: warning" in captured.out
    assert observed["mode"] == "preflight-paper"
    assert observed["result"] == "warning"


def test_preflight_entrypoint_does_not_start_live_loop(monkeypatch):
    monkeypatch.setattr(app_main, "setup_logging", lambda: None)
    monkeypatch.setattr(app_main, "load_config", lambda: make_bot_config(paper=False))
    monkeypatch.setattr(app_main, "_run_live_loop", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("live loop started")))
    monkeypatch.setattr(app_main, "log_run_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(preflight, "_check_trading_access", lambda config: ReadinessCheckResult("alpaca_trading_access", ReadinessStatus.PASS, "ok"))
    monkeypatch.setattr(preflight, "_check_market_data_access", lambda config: ReadinessCheckResult("alpaca_market_data_access", ReadinessStatus.PASS, "ok"))
    monkeypatch.setattr(preflight, "_check_news_access", lambda config: ReadinessCheckResult("alpaca_news_access", ReadinessStatus.PASS, "ok"))
    _patch_diagnostic_checks(monkeypatch)

    exit_code = app_main.main(["--mode", "preflight", "--preflight-target", "live"])

    assert exit_code == 2
