from __future__ import annotations

from datetime import datetime, timezone

from tradingbot.data.news import DataHandler
from tradingbot.data.offline_news import load_offline_news_directory, load_offline_news_fixture


def test_load_offline_news_fixture_filters_symbol_and_window(tmp_path):
    fixture = tmp_path / "news.csv"
    fixture.write_text(
        "symbol,published_at,headline,source\n"
        "SPY,2024-10-25T13:30:00+00:00,SPY rallies on earnings,fixture\n"
        "BTCUSD,2024-10-25T13:30:00+00:00,Bitcoin steadies,fixture\n"
        "SPY,2024-11-05T13:30:00+00:00,Outside window,fixture\n",
        encoding="utf-8",
    )

    loaded = load_offline_news_fixture(fixture)
    headlines = loaded.headlines_for(
        "SPY",
        start=datetime(2024, 10, 22, tzinfo=timezone.utc),
        end=datetime(2024, 11, 1, tzinfo=timezone.utc),
    )

    assert headlines == ["SPY rallies on earnings"]


def test_load_offline_news_directory_combines_csv_fixtures(tmp_path):
    (tmp_path / "spy.csv").write_text(
        "symbol,published_at,headline\nSPY,2024-10-25T13:30:00+00:00,SPY fixture\n",
        encoding="utf-8",
    )
    (tmp_path / "btc.csv").write_text(
        "symbol,published_at,headline\nBTCUSD,2024-10-25T13:30:00+00:00,BTC fixture\n",
        encoding="utf-8",
    )

    loaded = load_offline_news_directory(tmp_path)

    assert len(loaded.records) == 2


def test_data_handler_uses_offline_fixture_before_neutral_fallback(tmp_path):
    (tmp_path / "spy.csv").write_text(
        "symbol,published_at,headline\nSPY,2024-10-25T13:30:00+00:00,SPY fixture\n",
        encoding="utf-8",
    )
    handler = DataHandler(source="alpaca", offline_news_enabled=True, offline_news_dir=str(tmp_path))

    records = handler.get_news_records("SPY", "2024-10-22", "2024-11-01")

    assert [record["headline"] for record in records] == ["SPY fixture"]
    assert records[0]["sentiment_source"] == "local_fixture"
    assert handler.last_news_source == "local_fixture"


def test_data_handler_marks_neutral_fallback_when_offline_fixture_is_missing(tmp_path):
    handler = DataHandler(source="alpaca", offline_news_enabled=True, offline_news_dir=str(tmp_path))

    records = handler.get_news_records("SPY", "2024-10-22", "2024-11-01")

    assert records == []
    assert handler.last_news_source == "neutral_fallback"
