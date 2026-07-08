import requests
import json
import time
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

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
        db.session.commit()

# Below is code to find the right tickers, which are used to get the markets. We only want US election markets. 
BASE_URL = "https://external-api.kalshi.com/trade-api/v2"

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY",
    "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}

def get_series_list():
    response = requests.get(f"{BASE_URL}/series")
    response.raise_for_status()
    return response.json()["series"]

def is_us_election_series(series):
    ticker = series["ticker"].upper()
    for prefix in ("SENATE", "GOV"):
        if prefix in ticker:
            idx = ticker.find(prefix) + len(prefix)
            if ticker[idx:idx+2] in US_STATES:
                return True
    return False

def get_markets(series_ticker, status="open", limit=100):
    params = {"status": status, "limit": limit, "series_ticker": series_ticker}
    response = requests.get(f"{BASE_URL}/markets", params=params)
    response.raise_for_status()
    return response.json()["markets"]

if __name__ == "__main__":
    series_list = get_series_list()
    election_series = [s for s in series_list if s.get("category") == "Elections"]
    us_series = [s for s in election_series if is_us_election_series(s)]
    all_markets = []
    for series in us_series:
        markets = get_markets(series_ticker=series["ticker"])
        all_markets.extend(markets)
        time.sleep(0.3)
    all_markets = sorted(all_markets, key=lambda m: float(m["volume_fp"]), reverse=True)[:100]
    upsert_markets(all_markets)
