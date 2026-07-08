import unittest
from kalshi_ingest import normalize_kalshi_market, upsert_markets, Market, app

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

def test_normalize_kalshi_market():
    raw_market = {
        "ticker": "US2024-11-05-1",
        "event