from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class OfflineNewsRecord:
    symbol: str
    published_at: datetime
    headline: str
    source: str = "local_fixture"


@dataclass(frozen=True)
class OfflineNewsFixture:
    path: Path
    records: tuple[OfflineNewsRecord, ...]

    def headlines_for(self, symbol: str, start: datetime, end: datetime) -> list[str]:
        normalized_symbol = symbol.upper()
        return [
            record.headline
            for record in self.records
            if record.symbol.upper() == normalized_symbol and start <= record.published_at <= end
        ]


def parse_offline_news_rows(rows: Iterable[dict[str, str]]) -> tuple[OfflineNewsRecord, ...]:
    records: list[OfflineNewsRecord] = []
    for row in rows:
        symbol = (row.get("symbol") or "").strip().upper()
        headline = (row.get("headline") or "").strip()
        published_raw = (row.get("published_at") or "").strip()
        if not symbol or not headline or not published_raw:
            continue
        records.append(
            OfflineNewsRecord(
                symbol=symbol,
                published_at=_parse_datetime(published_raw),
                headline=headline,
                source=(row.get("source") or "local_fixture").strip() or "local_fixture",
            )
        )
    return tuple(records)


def load_offline_news_fixture(path: str | Path) -> OfflineNewsFixture:
    fixture_path = Path(path)
    with fixture_path.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return OfflineNewsFixture(path=fixture_path, records=parse_offline_news_rows(rows))


def _parse_datetime(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
