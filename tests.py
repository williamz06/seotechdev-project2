import unittest
from kalshi_ingest import normalize_kalshi_market, upsert_markets, Market, app

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

class TestNormalize(unittest.TestCase):
    def test_normalize_kalshi_market(self):
        example_market = {
            "ticker": "KXGOVFLNOMD-26-JDEM",
            "event_ticker": "KXGOVFLNOMD-26",
            "title": "Will Jerry Demings be the Democratic nominee for Governor in Florida?",
            "yes_sub_title": "Jerry Demings",
            "status": "active",
            "close_time": "2026-11-03T15:00:00Z",
            "last_price_dollars": "0.0230",
            "volume_fp": "7269.74",
            "updated_time": "2026-04-09T10:50:41.78994Z",
            "created_time": "2025-11-13T00:12:29.324539Z",
            "market_type": "binary",
        }
        expected_normalized = {
            "ticker": "KXGOVFLNOMD-26-JDEM",
            "event_ticker": "KXGOVFLNOMD-26",
            "title": "Will Jerry Demings be the Democratic nominee for Governor in Florida?",
            "candidate": "Jerry Demings",
            "status": "active",
            "close_time": "2026-11-03T15:00:00Z",
            "yes_price": 0.023,
            "no_price": 0.977,
            "volume": 7269.74,
            "observed_at": "2026-04-09T10:50:41.78994Z",
            "created_at": "2025-11-13T00:12:29.324539Z",
        }
        assert normalize_kalshi_market(example_market) == expected_normalized

if __name__ == "__main__":
    unittest.main()