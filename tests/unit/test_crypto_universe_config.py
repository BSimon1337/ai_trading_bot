from __future__ import annotations

import pytest

from tradingbot.config.crypto_universe import (
    ALPACA_TRADABLE_CRYPTO_PAIRS,
    ALPACA_USD_CRYPTO_PAIRS,
    crypto_universe_symbols,
    normalize_crypto_symbol,
)
from tradingbot.config.settings import load_config


def _base_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "key")
    monkeypatch.setenv("API_SECRET", "secret")
    monkeypatch.setenv("BACKTEST_START", "2024-01-01")
    monkeypatch.setenv("BACKTEST_END", "2024-02-01")
    monkeypatch.delenv("SYMBOL", raising=False)
    monkeypatch.delenv("SYMBOLS", raising=False)
    monkeypatch.delenv("CRYPTO_SYMBOLS", raising=False)
    monkeypatch.delenv("ALPACA_CRYPTO_UNIVERSE", raising=False)
    monkeypatch.delenv("PAPER_TRADING", raising=False)
    monkeypatch.delenv("DECISION_LOG_PATH", raising=False)
    monkeypatch.delenv("FILL_LOG_PATH", raising=False)
    monkeypatch.delenv("DAILY_SNAPSHOT_PATH", raising=False)


def test_normalize_crypto_symbol_accepts_common_alpaca_forms():
    assert normalize_crypto_symbol("btcusd") == "BTC/USD"
    assert normalize_crypto_symbol("eth-usdc") == "ETH/USDC"
    assert normalize_crypto_symbol("SOL/USDT") == "SOL/USDT"


def test_crypto_universe_usd_contains_usd_pairs_only():
    symbols = crypto_universe_symbols("usd")

    assert "BTC/USD" in symbols
    assert "ETH/USD" in symbols
    assert "BTC/USDC" not in symbols
    assert all(symbol.endswith("/USD") for symbol in symbols)


def test_crypto_universe_all_contains_non_usd_pairs():
    symbols = crypto_universe_symbols("all")

    assert symbols == ALPACA_TRADABLE_CRYPTO_PAIRS
    assert "ETH/BTC" in symbols
    assert len(symbols) > len(ALPACA_USD_CRYPTO_PAIRS)


def test_crypto_universe_rejects_unknown_name():
    with pytest.raises(ValueError, match="ALPACA_CRYPTO_UNIVERSE"):
        crypto_universe_symbols("moonbag")


def test_load_config_merges_stock_symbols_explicit_crypto_and_universe(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("SYMBOLS", "F,BTCUSD")
    monkeypatch.setenv("CRYPTO_SYMBOLS", "ethusd, sol-usd")
    monkeypatch.setenv("ALPACA_CRYPTO_UNIVERSE", "usd")

    config = load_config()

    assert config.symbols[0] == "F"
    assert "BTC/USD" in config.symbols
    assert "ETH/USD" in config.symbols
    assert "SOL/USD" in config.symbols
    assert config.symbols.count("BTC/USD") == 1
    assert config.asset_classes["ETH/USD"] == "crypto"


def test_load_config_defaults_live_log_paths_to_live_validation_scope(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("PAPER_TRADING", "0")
    monkeypatch.setenv("SYMBOLS", "ETH/USD")

    config = load_config()

    assert config.decision_log_path.endswith("logs\\live_validation_ethusd\\decisions.csv") or config.decision_log_path.endswith(
        "logs/live_validation_ethusd/decisions.csv"
    )
    assert config.fill_log_path.endswith("live_validation_ethusd\\fills.csv") or config.fill_log_path.endswith(
        "live_validation_ethusd/fills.csv"
    )
    assert config.daily_snapshot_path.endswith("live_validation_ethusd\\daily_snapshot.csv") or config.daily_snapshot_path.endswith(
        "live_validation_ethusd/daily_snapshot.csv"
    )


def test_load_config_keeps_explicit_log_paths(monkeypatch):
    _base_env(monkeypatch)
    monkeypatch.setenv("PAPER_TRADING", "0")
    monkeypatch.setenv("DECISION_LOG_PATH", "custom/decisions.csv")
    monkeypatch.setenv("FILL_LOG_PATH", "custom/fills.csv")
    monkeypatch.setenv("DAILY_SNAPSHOT_PATH", "custom/snapshot.csv")

    config = load_config()

    assert config.decision_log_path == "custom/decisions.csv"
    assert config.fill_log_path == "custom/fills.csv"
    assert config.daily_snapshot_path == "custom/snapshot.csv"
