from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, List

import pandas as pd

from tradingbot.data.offline_news import load_offline_news_directory

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional in bare environments
    def load_dotenv(*args, **kwargs) -> bool:
        return False


LOGGER = logging.getLogger(__name__)
DEFAULT_HEADLINE_PREVIEW_LIMIT = 3


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
        offline_news_enabled: bool | None = None,
        offline_news_dir: str | None = None,
    ):
        _load_env_files()
        self.source = source
        self.api_key = api_key or os.getenv("API_KEY", os.getenv("ALPACA_API_KEY", ""))
        self.api_secret = api_secret or os.getenv(
            "API_SECRET", os.getenv("ALPACA_API_SECRET", "")
        )
        self.base_url = base_url or os.getenv("BASE_URL", "https://paper-api.alpaca.markets")
        self.offline_news_enabled = _get_bool_env("OFFLINE_NEWS_ENABLED", False) if offline_news_enabled is None else offline_news_enabled
        self.offline_news_dir = offline_news_dir or os.getenv("OFFLINE_NEWS_DIR", "data/offline_news")
        self.last_news_source = "external"
        self.last_news_records: List[dict[str, Any]] = []
        self.last_headline_preview: list[str] = []
        self.last_headline_count = 0
        self.last_news_window_start = ""
        self.last_news_window_end = ""
        self.last_news_observed_at = ""
        self._stock_client: Any | None = None
        self._crypto_client: Any | None = None
        self._news_client: Any | None = None

    def _update_news_metadata(
        self,
        *,
        source: str,
        records: List[dict[str, Any]],
        start: str,
        end: str,
        preview_limit: int = DEFAULT_HEADLINE_PREVIEW_LIMIT,
    ) -> None:
        self.last_news_source = source
        self.last_news_records = list(records)
        self.last_headline_preview = [
            str(record.get("headline", "")).strip()
            for record in records
            if str(record.get("headline", "")).strip()
        ][:preview_limit]
        self.last_headline_count = len(self.last_headline_preview)
        if records:
            self.last_headline_count = sum(
                1 for record in records if str(record.get("headline", "")).strip()
            )
        self.last_news_window_start = start
        self.last_news_window_end = end
        self.last_news_observed_at = datetime.now(timezone.utc).isoformat()

    def _client_or_raise(self) -> tuple[Any, Any, Any]:
        from alpaca.data.historical import CryptoHistoricalDataClient, NewsClient, StockHistoricalDataClient

        if self.source != "alpaca":
            raise ValueError(f"Unsupported data source: {self.source}")
        if not self.api_key or not self.api_secret:
            raise ValueError("Missing Alpaca credentials for DataHandler.")
        if self._stock_client is None:
            self._stock_client = StockHistoricalDataClient(self.api_key, self.api_secret)
        if self._crypto_client is None:
            self._crypto_client = CryptoHistoricalDataClient(self.api_key, self.api_secret)
        if self._news_client is None:
            self._news_client = NewsClient(self.api_key, self.api_secret)
        return self._stock_client, self._crypto_client, self._news_client

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
        from alpaca.data.requests import NewsRequest

        if self.offline_news_enabled:
            records = self._get_offline_news_records(symbol=symbol, start=start, end=end, limit=limit)
            if records:
                self._update_news_metadata(
                    source="local_fixture",
                    records=records,
                    start=start,
                    end=end,
                )
                return records
            self._update_news_metadata(
                source="neutral_fallback",
                records=[],
                start=start,
                end=end,
            )
            LOGGER.warning(
                "Offline news enabled but no fixture records matched %s from %s to %s; using neutral sentiment fallback.",
                symbol,
                start,
                end,
            )
            return []

        _, _, news_client = self._client_or_raise()
        all_records: List[dict] = []
        page_token = None
        pages = 0

        while pages < max_pages:
            request = NewsRequest(
                symbols=symbol,
                start=pd.Timestamp(start, tz="UTC").to_pydatetime(),
                end=pd.Timestamp(end, tz="UTC").to_pydatetime(),
                limit=limit,
                page_token=page_token,
            )
            try:
                response = news_client.get_news(request)
            except Exception as exc:
                self._update_news_metadata(
                    source="neutral_fallback",
                    records=[],
                    start=start,
                    end=end,
                )
                LOGGER.warning(
                    "Alpaca news fetch failed for %s from %s to %s; using neutral sentiment fallback. Error: %s",
                    symbol,
                    start,
                    end,
                    exc,
                )
                break
            rows = []
            for item in response.data.get("news", []):
                raw = item.model_dump()
                if raw:
                    rows.append(raw)
            all_records.extend(rows)

            page_token = response.next_page_token
            pages += 1
            if not page_token:
                break

        self._update_news_metadata(
            source="external" if all_records else "neutral_fallback",
            records=all_records,
            start=start,
            end=end,
        )
        return all_records

    def _get_offline_news_records(self, symbol: str, start: str, end: str, limit: int) -> List[dict]:
        start_dt = pd.Timestamp(start, tz="UTC").to_pydatetime()
        end_dt = pd.Timestamp(end, tz="UTC").to_pydatetime()
        fixture = load_offline_news_directory(self.offline_news_dir)
        records = fixture.records_for(symbol=symbol, start=start_dt, end=end_dt)
        return [
            {
                "symbol": record.symbol,
                "published_at": record.published_at.isoformat(),
                "headline": record.headline,
                "source": record.source,
                "sentiment_source": "local_fixture",
            }
            for record in records[:limit]
        ]

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: str,
        end: str,
        adjustment: str = "raw",
        limit: int = 10000,
    ) -> pd.DataFrame:
        from alpaca.data.requests import CryptoBarsRequest, StockBarsRequest

        stock_client, crypto_client, _ = self._client_or_raise()
        df = pd.DataFrame()
        parsed_timeframe = self._parse_timeframe(timeframe)

        try:
            request = StockBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=parsed_timeframe,
                start=pd.Timestamp(start, tz="UTC").to_pydatetime(),
                end=pd.Timestamp(end, tz="UTC").to_pydatetime(),
                adjustment=adjustment,
                limit=limit,
            )
            bars = stock_client.get_stock_bars(request)
            df = bars.df.copy()
        except Exception:
            df = pd.DataFrame()

        if df.empty and self._is_crypto_symbol(symbol):
            crypto_symbol = self._normalize_crypto_symbol(symbol)
            try:
                request = CryptoBarsRequest(
                    symbol_or_symbols=crypto_symbol,
                    timeframe=parsed_timeframe,
                    start=pd.Timestamp(start, tz="UTC").to_pydatetime(),
                    end=pd.Timestamp(end, tz="UTC").to_pydatetime(),
                    limit=limit,
                )
                crypto_bars = crypto_client.get_crypto_bars(request)
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

    @staticmethod
    def _parse_timeframe(timeframe: str):
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        value = timeframe.strip()
        if not value:
            raise ValueError("Timeframe cannot be empty.")

        digits = "".join(ch for ch in value if ch.isdigit())
        unit_text = "".join(ch for ch in value if ch.isalpha()).lower()
        amount = int(digits) if digits else 1

        unit_map = {
            "min": TimeFrameUnit.Minute,
            "minute": TimeFrameUnit.Minute,
            "minutes": TimeFrameUnit.Minute,
            "hour": TimeFrameUnit.Hour,
            "hours": TimeFrameUnit.Hour,
            "day": TimeFrameUnit.Day,
            "days": TimeFrameUnit.Day,
            "week": TimeFrameUnit.Week,
            "weeks": TimeFrameUnit.Week,
            "month": TimeFrameUnit.Month,
            "months": TimeFrameUnit.Month,
        }
        if unit_text not in unit_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        return TimeFrame(amount, unit_map[unit_text])


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}
