from __future__ import annotations

from collections.abc import Iterable


# Snapshot of Alpaca tradable crypto pairs observed through the trading assets
# API. Operators can still use CRYPTO_SYMBOLS for narrower live allow-lists.
ALPACA_TRADABLE_CRYPTO_PAIRS: tuple[str, ...] = (
    "AAVE/USD",
    "AAVE/USDC",
    "AAVE/USDT",
    "ADA/USD",
    "ARB/USD",
    "AVAX/USD",
    "AVAX/USDC",
    "AVAX/USDT",
    "BAT/USD",
    "BAT/USDC",
    "BCH/BTC",
    "BCH/USD",
    "BCH/USDC",
    "BCH/USDT",
    "BONK/USD",
    "BTC/USD",
    "BTC/USDC",
    "BTC/USDT",
    "CRV/USD",
    "CRV/USDC",
    "DOGE/USD",
    "DOGE/USDC",
    "DOGE/USDT",
    "DOT/USD",
    "DOT/USDC",
    "ETH/BTC",
    "ETH/USD",
    "ETH/USDC",
    "ETH/USDT",
    "FIL/USD",
    "GRT/USD",
    "GRT/USDC",
    "HYPE/USD",
    "LDO/USD",
    "LINK/BTC",
    "LINK/USD",
    "LINK/USDC",
    "LINK/USDT",
    "LTC/BTC",
    "LTC/USD",
    "LTC/USDC",
    "LTC/USDT",
    "ONDO/USD",
    "PAXG/USD",
    "PEPE/USD",
    "POL/USD",
    "RENDER/USD",
    "SHIB/USD",
    "SHIB/USDC",
    "SHIB/USDT",
    "SKY/USD",
    "SOL/USD",
    "SOL/USDC",
    "SOL/USDT",
    "SUSHI/USD",
    "SUSHI/USDC",
    "SUSHI/USDT",
    "TRUMP/USD",
    "UNI/BTC",
    "UNI/USD",
    "UNI/USDC",
    "UNI/USDT",
    "USDC/USD",
    "USDG/USD",
    "USDT/USD",
    "USDT/USDC",
    "WIF/USD",
    "XRP/USD",
    "XTZ/USD",
    "XTZ/USDC",
    "YFI/USD",
    "YFI/USDC",
    "YFI/USDT",
)

ALPACA_USD_CRYPTO_PAIRS: tuple[str, ...] = tuple(
    symbol for symbol in ALPACA_TRADABLE_CRYPTO_PAIRS if symbol.endswith("/USD")
)


def normalize_crypto_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper().replace("-", "/")
    if "/" in normalized:
        return normalized
    for quote in ("USDC", "USDT", "USD", "BTC"):
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return f"{normalized[:-len(quote)]}/{quote}"
    return normalized


def crypto_universe_symbols(name: str) -> tuple[str, ...]:
    normalized = name.strip().lower()
    if normalized in {"", "none", "off", "false", "0"}:
        return ()
    if normalized in {"usd", "usd_pairs", "alpaca_usd"}:
        return ALPACA_USD_CRYPTO_PAIRS
    if normalized in {"all", "alpaca", "alpaca_all"}:
        return ALPACA_TRADABLE_CRYPTO_PAIRS
    raise ValueError(
        "ALPACA_CRYPTO_UNIVERSE must be one of: none, usd, all."
    )


def dedupe_symbols(symbols: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return tuple(result)
