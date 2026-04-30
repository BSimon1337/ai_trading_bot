from __future__ import annotations

from tests.conftest import make_bot_config
from tradingbot.app import main as main_module


def test_runtime_manager_entrypoint_starts_requested_symbol(monkeypatch):
    calls: dict[str, object] = {}

    monkeypatch.setattr(main_module, "load_config", lambda: make_bot_config(symbols=("BTC/USD", "ETH/USD")))

    def fake_run_runtime_manager_start(config, *, symbols):
        calls["config"] = config
        calls["symbols"] = symbols
        return 0

    monkeypatch.setattr(main_module, "_run_runtime_manager_start", fake_run_runtime_manager_start)

    exit_code = main_module.main(["--mode", "runtime-start", "--managed-symbol", "ETH/USD"])

    assert exit_code == 0
    assert calls["symbols"] == ("ETH/USD",)


def test_runtime_manager_entrypoint_defaults_to_configured_symbols(monkeypatch):
    calls: dict[str, object] = {}

    monkeypatch.setattr(main_module, "load_config", lambda: make_bot_config(symbols=("BTC/USD", "ETH/USD")))

    def fake_run_runtime_manager_start(config, *, symbols):
        calls["config"] = config
        calls["symbols"] = symbols
        return 0

    monkeypatch.setattr(main_module, "_run_runtime_manager_start", fake_run_runtime_manager_start)

    exit_code = main_module.main(["--mode", "runtime-start"])

    assert exit_code == 0
    assert calls["symbols"] == ("BTC/USD", "ETH/USD")


def test_runtime_manager_entrypoint_stops_requested_symbol(monkeypatch):
    calls: dict[str, object] = {}

    monkeypatch.setattr(main_module, "load_config", lambda: make_bot_config(symbols=("BTC/USD", "ETH/USD")))

    def fake_run_runtime_manager_stop(config, *, symbols):
        calls["config"] = config
        calls["symbols"] = symbols
        return 0

    monkeypatch.setattr(main_module, "_run_runtime_manager_stop", fake_run_runtime_manager_stop)

    exit_code = main_module.main(["--mode", "runtime-stop", "--managed-symbol", "BTC/USD"])

    assert exit_code == 0
    assert calls["symbols"] == ("BTC/USD",)


def test_runtime_manager_entrypoint_restarts_requested_symbol(monkeypatch):
    calls: dict[str, object] = {}

    monkeypatch.setattr(main_module, "load_config", lambda: make_bot_config(symbols=("BTC/USD", "ETH/USD")))

    def fake_run_runtime_manager_restart(config, *, symbols):
        calls["config"] = config
        calls["symbols"] = symbols
        return 0

    monkeypatch.setattr(main_module, "_run_runtime_manager_restart", fake_run_runtime_manager_restart)

    exit_code = main_module.main(["--mode", "runtime-restart", "--managed-symbol", "ETH/USD"])

    assert exit_code == 0
    assert calls["symbols"] == ("ETH/USD",)
