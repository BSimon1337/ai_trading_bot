from __future__ import annotations

import os
from typing import List

import pandas as pd
from alpaca_trade_api import REST
from dotenv import load_dotenv


def _load_env_files() -> None:
    load_dotenv(dotenv_path=".env", override=False)
    load_dotenv(dotenv_path="env/.env", override=False)


class DataHandler:
    def __init__(
        self,
        source: str = "alpaca",
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str | None = None,
    ):
        _load_env_files()
        self.source = source
        self.api_key = api_key or os.getenv("API_KEY", os.getenv("ALPACA_API_KEY", ""))
        self.api_secret = api_secret or os.getenv(
            "API_SECRET", os.getenv("ALPACA_API_SECRET", "")
        )
        self.base_url = base_url or os.getenv("BASE_URL", "https://paper-api.alpaca.markets")
        self._client: REST | None = None

    def _client_or_raise(self) -> REST:
        if self.source != "alpaca":
            raise ValueError(f"Unsupported data source: {self.source}")
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca credentials for DataHandler.")
        if self._client is None:
            self._client = REST(
                key_id=self.api_key,
                secret_key=self.api_secret,
                base_url=self.base_url,
            )
        return self._client

    def get_news_headlines(self, symbol: str, start: str, end: str, limit: int = 200) -> List[str]:
        records = self.get_news_records(symbol=symbol, start=start, end=end, limit=limit)
        return [record.get("headline", "") for record in records if record.get("headline")]

    def get_news_records(
        self,
        symbol: str,
        start: str,
        end: str,
        limit: int = 200,
        max_pages: int = 50,
    ) -> List[dict]:
        client = self._client_or_raise()
        all_records: List[dict] = []
        page_token = None
        pages = 0

        while pages < max_pages:
            try:
                news = client.get_news(
                    symbol=symbol,
                    start=start,
                    end=end,
                    limit=limit,
                    page_token=page_token,
                )
            except TypeError:
                # Older alpaca_trade_api versions do not support page_token.
                news = client.get_news(
                    symbol=symbol,
                    start=start,
                    end=end,
                    limit=limit,
                )
                page_token = None
            rows = []
            for item in news:
                raw = item.__dict__.get("_raw", {})
                if raw:
                    rows.append(raw)
            all_records.extend(rows)

            page_token = getattr(news, "next_page_token", None)
            pages += 1
            if not page_token:
                break

        return all_records

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        adjustment: str = "raw",
        limit: int = 10000,
    ) -> pd.DataFrame:
        client = self._client_or_raise()
        df = pd.DataFrame()

        try:
            bars = client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
                adjustment=adjustment,
                limit=limit,
            )
            df = bars.df.copy()
        except Exception:
            df = pd.DataFrame()

        if df.empty and self._is_crypto_symbol(symbol):
            crypto_symbol = self._normalize_crypto_symbol(symbol)
            try:
                crypto_bars = client.get_crypto_bars(
                    crypto_symbol,
                    timeframe,
                    start,
                    end,
                    limit=limit,
                )
                df = crypto_bars.df.copy()
            except Exception:
                df = pd.DataFrame()

        if df.empty:
            return df

        if isinstance(df.index, pd.MultiIndex):
            try:
                df = df.xs(symbol, level=0)
            except Exception:
                # If the symbol level is not present, keep original index.
                pass

        df = df.reset_index()
        if "timestamp" not in df.columns and "index" in df.columns:
            df = df.rename(columns={"index": "timestamp"})
        if "symbol" not in df.columns:
            df["symbol"] = symbol
        return df

    @staticmethod
    def _is_crypto_symbol(symbol: str) -> bool:
        normalized = symbol.upper().replace("-", "/")
        if "/" in normalized:
            return True
        return normalized.endswith("USD") and len(normalized) > 3

    @staticmethod
    def _normalize_crypto_symbol(symbol: str) -> str:
        normalized = symbol.upper().replace("-", "/")
        if "/" in normalized:
            return normalized
        if normalized.endswith("USD") and len(normalized) > 3:
            base = normalized[:-3]
            return f"{base}/USD"
        return normalized
