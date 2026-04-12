from __future__ import annotations

from tradingbot.app import preflight
from tradingbot.app.preflight import ReadinessCheckResult, ReadinessStatus
from tests.conftest import make_bot_config


def _passing_probe(config):
    return ReadinessCheckResult("probe", ReadinessStatus.PASS, "ok")


def test_preflight_passes_when_required_checks_are_ready(tmp_path, monkeypatch):
    config = make_bot_config(
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )
    monkeypatch.setattr(preflight, "_check_trading_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_market_data_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_news_access", _passing_probe)

    report = preflight.run_preflight(config, target_mode="paper")

    assert report.overall_status == ReadinessStatus.PASS
    assert report.exit_code == 0


def test_preflight_fails_when_credentials_are_missing(tmp_path, monkeypatch):
    config = make_bot_config(
        api_key="",
        api_secret="",
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )
    monkeypatch.setattr(preflight, "_check_trading_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_market_data_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_news_access", _passing_probe)

    report = preflight.run_preflight(config, target_mode="paper")

    assert report.overall_status == ReadinessStatus.FAIL
    assert report.exit_code == 2
    assert any(check.name == "credentials" for check in report.failed_checks)


def test_preflight_reports_warnings_without_blocking_safe_modes(tmp_path, monkeypatch):
    config = make_bot_config(
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )
    monkeypatch.setattr(preflight, "_check_trading_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_market_data_access", _passing_probe)
    monkeypatch.setattr(
        preflight,
        "_check_news_access",
        lambda config: ReadinessCheckResult("alpaca_news_access", ReadinessStatus.WARNING, "news unavailable"),
    )

    report = preflight.run_preflight(config, target_mode="backtest")

    assert report.overall_status == ReadinessStatus.WARNING
    assert report.exit_code == 1
    assert "alpaca_news_access" in report.to_text()


def test_preflight_blocks_live_readiness_when_live_flags_are_missing(tmp_path, monkeypatch):
    config = make_bot_config(
        paper=False,
        live_trading_enabled=False,
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )
    monkeypatch.setattr(preflight, "_check_trading_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_market_data_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_news_access", _passing_probe)

    report = preflight.run_preflight(config, target_mode="live")

    assert report.overall_status == ReadinessStatus.FAIL
    assert any(check.name == "live_safeguards" for check in report.failed_checks)
    assert "LIVE_TRADING_ENABLED" in report.to_text()


def test_preflight_rejects_paper_mode_as_live_readiness(tmp_path, monkeypatch):
    config = make_bot_config(
        paper=True,
        live_trading_enabled=True,
        live_run_confirmation="CONFIRM",
        decision_log_path=str(tmp_path / "logs" / "decisions.csv"),
        fill_log_path=str(tmp_path / "logs" / "fills.csv"),
        daily_snapshot_path=str(tmp_path / "logs" / "daily_snapshot.csv"),
    )
    monkeypatch.setattr(preflight, "_check_trading_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_market_data_access", _passing_probe)
    monkeypatch.setattr(preflight, "_check_news_access", _passing_probe)

    report = preflight.run_preflight(config, target_mode="live")

    assert report.overall_status == ReadinessStatus.FAIL
    assert "PAPER_TRADING" in report.to_text()
