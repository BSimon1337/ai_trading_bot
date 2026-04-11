from __future__ import annotations

import sys
import types

from tradingbot.data.news import DataHandler


def test_news_fetch_failure_returns_empty_records(monkeypatch):
    class FakeNewsRequest:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeNewsClient:
        def get_news(self, request):
            raise RuntimeError("401 Unauthorized")

    fake_requests = types.ModuleType("alpaca.data.requests")
    fake_requests.NewsRequest = FakeNewsRequest
    monkeypatch.setitem(sys.modules, "alpaca.data.requests", fake_requests)

    handler = DataHandler(api_key="key", api_secret="secret")
    monkeypatch.setattr(handler, "_client_or_raise", lambda: (None, None, FakeNewsClient()))

    assert handler.get_news_records("SPY", "2024-10-19", "2024-10-22") == []
    assert handler.get_news_headlines("SPY", "2024-10-19", "2024-10-22") == []
