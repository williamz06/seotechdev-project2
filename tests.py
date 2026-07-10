import unittest
from api.kalshi_ingest import normalize_kalshi_market, get_markets
from app import app as flask_app
from unittest.mock import patch
from datetime import datetime, timezone
from api.bluesky_prod import iso_z, flatten_post
from types import SimpleNamespace
from prediction.classify_predict import classify_post

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
            "url": "https://kalshi.com/markets/kxgovflnomd/market/kxgovflnomd-26?op_market_ticker=KXGOVFLNOMD-26-JDEM",
        }
        assert normalize_kalshi_market(example_market) == expected_normalized

class TestPages(unittest.TestCase):
    def test_dashboard_page_exist(self):
        client = flask_app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)

class FakeResponse:
    def __init__(self, data):
        self._data = data
    def json(self):
        return self._data
    def raise_for_status(self):
        pass

class TestMockedRequests(unittest.TestCase):
    @patch("api.kalshi_ingest.requests.get")
    def test_get_markets(self, mock_get):
        mock_get.return_value = FakeResponse({"markets": [{"ticker": "FAKE-1"}]})
        result = get_markets(series_ticker="FAKE")
        self.assertEqual(result, [{"ticker": "FAKE-1"}])
        mock_get.assert_called_once()

class TestBlueskyProd(unittest.TestCase):
    def test_iso_z(self):
        dt = datetime(2026, 7, 6, 18, 30, 0, tzinfo=timezone.utc)
        result = iso_z(dt)
        self.assertEqual(result, "2026-07-06T18:30:00Z")

    def test_flatten_post(self):
        post = SimpleNamespace(
            uri="at://did:plc:abc/app.bsky.feed.post/123",
            cid="bafyabc",
            author=SimpleNamespace(handle="someuser.bsky.social", did="did:plc:abc"),
            record=SimpleNamespace(text="Hello world", langs=["en"], created_at="2026-07-06T18:00:00Z"),
            indexed_at="2026-07-06T18:00:05Z",
            like_count=5,
            repost_count=2,
            reply_count=1,
            quote_count=0,
        )
        result = flatten_post(post, "test_query", "macro_market")
        self.assertEqual(result["author_handle"], "someuser.bsky.social")
        self.assertEqual(result["text"], "Hello world")
        self.assertEqual(result["like_count"], 5)
        self.assertEqual(result["source_query"], "test_query")

class FakeOllamaResponse:
    def __init__(self, content):
        self.content = content
    def __getitem__(self, key):
        return {"message": {"content": self.content}}[key]

class TestOllamaResponse(unittest.TestCase):
    @patch("prediction.classify_predict.ollama.chat")
    def test_classify_post(self, mock_chat):
        mock_chat.return_value = FakeOllamaResponse('{"is_predictive": true, "predicted_party": "Democrat", "confidence": "High", "reason": "test"}')
        result = classify_post("I think the Democrat wins this one")
        self.assertTrue(result.is_predictive)
        self.assertEqual(result.predicted_party, "Democrat")

if __name__ == "__main__":
    unittest.main()