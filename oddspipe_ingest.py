import os
from dotenv import load_dotenv
from oddspipe import OddsPipe
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

load_dotenv()
odds_pipe = OddsPipe(api_key=os.getenv("ODDSPIPE_APIKEY"))

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'markets.db')
db = SQLAlchemy(app)

class Market(db.Model):
    market_id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String)
    platform_market_id = db.Column(db.String)
    title = db.Column(db.String)
    category = db.Column(db.String)
    status = db.Column(db.String)
    url = db.Column(db.String)
    created_at = db.Column(db.String)
    yes_price = db.Column(db.Float)
    no_price = db.Column(db.Float)
    volume = db.Column(db.Float)
    observed_at = db.Column(db.String)

    def __repr__(self):
        return f"Market('{self.title}', '{self.platform}')"

with app.app_context():
    db.create_all()
    
def get_markets():  
    markets = odds_pipe.markets(limit=5)
    normalized_markets = []
    for item in markets["items"]:
        normalized_market = normalize_market(item)
        normalized_markets.append(normalized_market)
    return normalized_markets

def normalize_market(item):
    source = item["source"]
    price = source["latest_price"]
    return {
        "market_id": item["id"],
        "platform": source["platform"],
        "platform_market_id": source["platform_market_id"],
        "title": item["title"],
        "category": item["category"],
        "status": item["status"],
        "url": source["url"],
        "created_at": item["created_at"],
        "yes_price": price["yes_price"],
        "no_price": price["no_price"],
        "volume": price["volume_usd"],
        "observed_at": price["snapshot_at"],
    }

def upsert_markets(markets):
    with app.app_context():
        for market in markets:
            existing_market = Market.query.filter_by(market_id=market["market_id"]).first()
            if existing_market:
                existing_market.platform = market["platform"]
                existing_market.platform_market_id = market["platform_market_id"]
                existing_market.title = market["title"]
                existing_market.category = market["category"]
                existing_market.status = market["status"]
                existing_market.url = market["url"]
                existing_market.created_at = market["created_at"]
                existing_market.yes_price = market["yes_price"]
                existing_market.no_price = market["no_price"]
                existing_market.volume = market["volume"]
                existing_market.observed_at = market["observed_at"]
            else:
                new_market = Market(
                    market_id=market["market_id"],
                    platform=market["platform"],
                    platform_market_id=market["platform_market_id"],
                    title=market["title"],
                    category=market["category"],
                    status=market["status"],
                    url=market["url"],
                    created_at=market["created_at"],
                    yes_price=market["yes_price"],
                    no_price=market["no_price"],
                    volume=market["volume"],
                    observed_at=market["observed_at"],
                )
                db.session.add(new_market)
        db.session.commit()

if __name__ == "__main__":
    upsert_markets(get_markets())