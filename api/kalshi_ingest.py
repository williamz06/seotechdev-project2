import re
import os
import time
import argparse
import requests
from datetime import datetime, timedelta, timezone
from itertools import groupby
from urllib.parse import urlparse

import pandas as pd
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from atproto import Client

try:
    from api.bluesky_prod import search_all_pages, flatten_post, iso_z
except ImportError:
    from bluesky_prod import search_all_pages, flatten_post, iso_z

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'markets.db')
db = SQLAlchemy(app)

class Market(db.Model):
    ticker = db.Column(db.String, primary_key=True)
    event_ticker = db.Column(db.String)
    title = db.Column(db.String)
    candidate = db.Column(db.String)
    status = db.Column(db.String)
    close_time = db.Column(db.String)
    yes_price = db.Column(db.Float)
    no_price = db.Column(db.Float)
    volume = db.Column(db.Float)
    observed_at = db.Column(db.String)
    created_at = db.Column(db.String)

    def __repr__(self):
        return f"Market('{self.ticker}', '{self.title}', yes={self.yes_price})"

class PriceHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String, db.ForeignKey('market.ticker'))
    yes_price = db.Column(db.Float)
    volume = db.Column(db.Float)
    observed_at = db.Column(db.String)

    def __repr__(self):
        return f"PriceHistory('{self.ticker}', yes={self.yes_price}, volume={self.volume}, observed_at={self.observed_at})"

with app.app_context():
    db.create_all()

def normalize_kalshi_market(m):
    yes_price = float(m["last_price_dollars"])
    return {
        "ticker": m["ticker"],
        "event_ticker": m["event_ticker"],
        "title": m["title"],
        "candidate": m.get("yes_sub_title"),
        "status": m["status"],
        "close_time": m["close_time"],
        "yes_price": yes_price,
        "no_price": 1 - yes_price,
        "volume": float(m["volume_fp"]),
        "observed_at": m["updated_time"],
        "created_at": m["created_time"],
    }

def upsert_markets(markets):
    with app.app_context():
        for raw in markets:
            market = normalize_kalshi_market(raw)
            existing = Market.query.filter_by(ticker=market["ticker"]).first()
            if existing:
                existing.event_ticker = market["event_ticker"]
                existing.title = market["title"]
                existing.candidate = market["candidate"]
                existing.status = market["status"]
                existing.close_time = market["close_time"]
                existing.yes_price = market["yes_price"]
                existing.no_price = market["no_price"]
                existing.volume = market["volume"]
                existing.observed_at = market["observed_at"]
            else:
                new_market = Market(**market)
                db.session.add(new_market)

            db.session.add(PriceHistory(
                ticker=market["ticker"],
                yes_price=market["yes_price"],
                volume=market["volume"],
                observed_at=market["observed_at"],
            ))
        db.session.commit()

BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

def get_series_list(tags = None):
    params = {"tags": tags} if tags else {}
    response = requests.get(f"{BASE_URL}/series", params=params)
    response.raise_for_status()
    return response.json()["series"]

def get_markets(series_ticker=None, event_ticker=None, status="open", limit=100):
    params = {"status": status, "limit": limit}
    if series_ticker:
        params["series_ticker"] = series_ticker
    if event_ticker:
        params["event_ticker"] = event_ticker
    response = requests.get(f"{BASE_URL}/markets", params=params)
    response.raise_for_status()
    return response.json()["markets"]

# User can add a URL
def parse_kalshi_url(url: str) -> tuple[str, str]:
    """
    Extract (series_ticker, event_ticker) from a Kalshi market URL.
    e.g. https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028
    gets ('KXPRESPARTY', 'KXPRESPARTY-2028')

    - It shows in the event-ticker at the end
    """
    path = urlparse(url).path
    parts = [p for p in path.split('/') if p]
    # expected: ['markets', '<series>', '<slug>', '<event>']

    if len(parts) < 4 or parts[0] != 'markets':
        raise ValueError(f"Unrecognized Kalshi URL format: {url}")
    return parts[1].upper(), parts[3].upper()

# Contract eligibility filter
# Binary contracts
# exclude over,under, numeric, non-winner or deterministic questions

_OVER_UNDER_RE = re.compile(
    r'\b(over|under|more than|fewer than|less than|at least|at most)\b.{0,30}\d',
    re.IGNORECASE
)
_NUMERIC_THRESHOLD_RE = re.compile(
    r'\d+\s*(seats|electoral votes|percent|%|delegates)',
    re.IGNORECASE
)
_WINNER_RE = re.compile(
    r'\b(win|wins|winner|elected|president|senator|governor|nominee|candidate)\b',
    re.IGNORECASE
)

def is_eligible_contract(raw_market: dict) -> bool:
    """
    True for deterministic yes/no US winner-prediction binary contracts.
    Excludes: over/under thresholds, numeric seat/vote counts, non-winner questions.
    """
    title = (raw_market.get("title") or "")
    if _OVER_UNDER_RE.search(title):
        return False
    if _NUMERIC_THRESHOLD_RE.search(title):
        return False
    if not _WINNER_RE.search(title):
        return False
    return True

# Party Look up

_CANDIDATE_PARTY = {
    "harris": "democrat",   "newsom": "democrat",   "shapiro": "democrat",
    "buttigieg": "democrat","warren": "democrat",   "whitmer": "democrat",
    "pritzker": "democrat", "beshear": "democrat",  "biden": "democrat",
    "trump": "republican",  "vance": "republican",  "desantis": "republican",
    "haley": "republican",  "rubio": "republican",  "scott": "republican",
    "pompeo": "republican", "cotton": "republican", "youngkin": "republican",
    "rfk": "third_party",   "kennedy": "third_party","west": "third_party",
    "stein": "third_party",
}

_PARTY_BASE_QUERIES = {
    "democrat":    ["Democrats", "Democrat", "DNC", "Blue wave"],
    "republican":  ["Republicans", "Republican", "GOP", "Red wave", "MAGA"],
    "third_party": ["Third party", "Libertarian", "Green party", "RFK Jr"],
}

def _candidate_party(name: str) -> str | None:
    for token in name.lower().split():
        if token in _CANDIDATE_PARTY:
            return _CANDIDATE_PARTY[token]
    return None

# Bluesky config builder

def build_bluesky_config(event_ticker: str, raw_markets: list[dict], window_hours: int = 6) -> dict:
    """
    Derive Bluesky search parameters from a group of raw Kalshi markets
    sharing the same event_ticker.

    Targeting deterministic US election contracts

    window_hours: how far back (and forward) from now to search for posts.
    """
    representative = max(raw_markets, key=lambda m: float(m.get("volume_fp") or 0))
    title = representative.get("title") or ""
    title_lower = title.lower()

    event_id = re.sub(r'[^A-Z0-9]', '_', event_ticker.upper()).strip('_')

    is_presidential = any(k in title_lower for k in ["president", "presidential", "white house"])
    is_senate       = "senate" in title_lower
    is_governor     = any(k in title_lower for k in ["governor", "gubernatorial"])

    # Gather candidate names across all markets in this event
    candidates = [m.get("yes_sub_title") for m in raw_markets if m.get("yes_sub_title")]

    options_queries: dict[str, list[str]] = {"democrat": [], "republican": [], "third_party": []}
    unknown_candidates = []

    for name in candidates:
        party = _candidate_party(name)
        if party:
            if name not in options_queries[party]:
                options_queries[party].append(name)
        else:
            unknown_candidates.append(name)

    # Append base party terms (deduped)
    for party, base_terms in _PARTY_BASE_QUERIES.items():
        seen = set(options_queries[party])
        for t in base_terms:
            if t not in seen:
                options_queries[party].append(t)
                seen.add(t)

    # Market-level queries
    if is_presidential:
        market_queries = [
            "2028 election", "2028 presidential", "next president 2028",
            "polymarket 2028", "election contract",
        ] + unknown_candidates
    elif is_senate:
        state = (re.search(r'\b([A-Z]{2})\b', event_ticker) or re.search(r'([A-Z]{2})', event_ticker))
        state = state.group(1) if state else ""
        market_queries = [
            f"{state} senate", f"{state} senate race", "senate election",
        ] + unknown_candidates
    elif is_governor:
        state = (re.search(r'\b([A-Z]{2})\b', event_ticker) or re.search(r'([A-Z]{2})', event_ticker))
        state = state.group(1) if state else ""
        market_queries = [
            f"{state} governor", f"{state} governor race", "gubernatorial",
        ] + unknown_candidates
    else:
        market_queries = ([title[:60]] if title else []) + unknown_candidates

    resolution_queries = [
        "election resolution", "associated press call",
        "fox news call", "nbc call", "election results",
    ]

    kickoff = datetime.now(timezone.utc)

    return {
        "event_id":          event_id,
        "kickoff":           kickoff,
        "match_minutes":     0,
        "window_pad_min":    window_hours * 60,
        "market_queries":    [q for q in market_queries if q],
        "options_queries":   {k: v for k, v in options_queries.items() if v},
        "resolution_queries": resolution_queries,
        "output_csv":        f"BLUESKY_POSTS_{event_id}.csv",
    }

# Bluesky fetcher

def fetch_bluesky_for_event(config: dict, bluesky_client) -> list[dict]:
    """Run Bluesky keyword search for one Kalshi event and return post rows."""
    kickoff = config["kickoff"]
    since   = iso_z(kickoff - timedelta(minutes=config["window_pad_min"]))
    until   = iso_z(kickoff + timedelta(minutes=config["match_minutes"] + config["window_pad_min"]))

    print(f"\n[Bluesky] {config['event_id']}  window: {since} ----> {until}")

    plan = [(q, "macro_market")     for q in config["market_queries"]]
    plan += [(q, "resolution_clause") for q in config["resolution_queries"]]
    for category, queries in config["options_queries"].items():
        plan += [(q, f"party_{category}") for q in queries]

    rows_by_uri: dict[str, dict] = {}
    for query, team in plan:
        posts = search_all_pages(bluesky_client, query, since, until, 5000)
        for p in posts:
            row = flatten_post(p, query, team)
            rows_by_uri.setdefault(row["uri"], row)
        time.sleep(0.3)

    rows = list(rows_by_uri.values())
    print(f"[Bluesky] {len(rows)} unique posts -> {config['output_csv']}")
    return rows

# Entry point

if __name__ == "__main__":
    load_dotenv()

    # CLI url optional
    parser = argparse.ArgumentParser(description="Kalshi ingest + Bluesky fetch")
    parser.add_argument(
        "--url",
        help="Kalshi market URL for a specific contract, e.g. https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028",
    )
    args = parser.parse_args()

    bluesky_client = Client()
    bluesky_client.login(os.getenv("BLUESKY_USERNAME"), os.getenv("BLUESKY_PASSWORD"))

    if args.url:
        # Single-contract flow
        series_ticker, event_ticker = parse_kalshi_url(args.url)
        print(f"Fetching contract: series={series_ticker}  event={event_ticker}")

        markets = get_markets(event_ticker=event_ticker)
        markets = [m for m in markets if m.get("market_type") == "binary" and is_eligible_contract(m)]

        if not markets:
            print("No eligible markets found for this contract.")
        else:
            upsert_markets(markets)
            config = build_bluesky_config(event_ticker, markets)
            rows = fetch_bluesky_for_event(config, bluesky_client)
            if rows:
                pd.DataFrame(rows).to_csv(config["output_csv"], index=False)

    # Then fetch all related US elections
    else:
        # Bulk flow — all US Elections series
        us_series = get_series_list(tags="US Elections")
        all_markets = []
        for series in us_series:
            markets = get_markets(series_ticker=series["ticker"])
            markets = [
                m for m in markets
                if m.get("market_type") == "binary" and is_eligible_contract(m)
            ]
            all_markets.extend(markets)
            time.sleep(0.3)

        print(f"{len(all_markets)} eligible markets found")
        all_markets = sorted(all_markets, key=lambda m: float(m["volume_fp"]), reverse=True)[:100]
        upsert_markets(all_markets)

        sorted_markets = sorted(all_markets, key=lambda m: m["event_ticker"])
        for event_ticker, group in groupby(sorted_markets, key=lambda m: m["event_ticker"]):
            event_markets = list(group)
            config = build_bluesky_config(event_ticker, event_markets)
            rows = fetch_bluesky_for_event(config, bluesky_client)
            if rows:
                pd.DataFrame(rows).to_csv(config["output_csv"], index=False)