import os
import sqlite3
import csv

from flask import Flask, abort, jsonify, render_template

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "api", "markets.db")
SOCIAL_FILES = {
    "KXPRESPARTY-2028": "classified_US_PREZ_2028_BASELINE.csv",
    "CONTROLH-2026": "prediction/output/classified_CONTROLH_2026.csv",
    "CONTROLS-2026": "prediction/output/classified_CONTROLS_2026.csv",
    "KXCAGOVPRIMARY1ST-26JUN02-1ST": "prediction/output/classified_KXCAGOVPRIMARY1ST_26JUN02_1ST.csv",
}

CANDIDATE_PARTIES = {
    "xavier becerra": "Democrat",
    "steve hilton": "Republican",
}

EVENT_NAMES = {
    "KXPRESPARTY-2028": "2028 Presidential Election: Party Winner",
    "CONTROLH-2026": "2026 U.S. House Control",
    "CONTROLS-2026": "2026 U.S. Senate Control",
    "KXCAGOVPRIMARY1ST-26JUN02-1ST": "2026 California Governor Primary",
}

PARTY_LABEL_TO_SUPPORT = {
    "Democrat": "Republican",
    "Republican": "Democrat",
}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_contract(row):
    return {
        "ticker": row["ticker"],
        "title": row["title"],
        "outcome_label": row["candidate"],
        "status": row["status"],
        "close_time": row["close_time"],
        "yes_price": row["yes_price"],
        "no_price": row["no_price"],
        "volume": row["volume"],
        "observed_at": row["observed_at"],
        "created_at": row["created_at"],
    }


def get_event(event_ticker, rows):
    contracts = []
    total_volume = 0
    last_updated = None
    has_active_contract = False

    for row in rows:
        contract = get_contract(row)
        contracts.append(contract)
        total_volume += contract["volume"] or 0

        if contract["status"] == "active":
            has_active_contract = True
        if contract["observed_at"] and (not last_updated or contract["observed_at"] > last_updated):
            last_updated = contract["observed_at"]

    contracts.sort(key=lambda contract: contract["volume"] or 0, reverse=True)

    return {
        "event_ticker": event_ticker,
        "display_name": EVENT_NAMES.get(event_ticker, event_ticker),
        "platform": "Kalshi",
        "contract_count": len(contracts),
        "status": "active" if has_active_contract else contracts[0]["status"],
        "volume": total_volume,
        "last_updated": last_updated,
        "contracts": contracts,
    }


def load_social_data(event_ticker):
    filename = SOCIAL_FILES.get(event_ticker)
    if not filename:
        return None

    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return None
    posts = []
    seen_uris = set()
    authors = set()
    post_count = 0

    with open(path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            post_count += 1
            if row["author_handle"]:
                authors.add(row["author_handle"])

            if row["uri"] in seen_uris:
                continue
            if row["is_predictive"] != "True":
                continue
            if row["predicted_party"] not in PARTY_LABEL_TO_SUPPORT:
                continue

            seen_uris.add(row["uri"])
            posts.append({
                "author": row["author_handle"],
                "text": row["text"],
                "created_at": row["created_at"],
                "like_count": int(row["like_count"] or 0),
                "supported_party": PARTY_LABEL_TO_SUPPORT[row["predicted_party"]],
            })

    return {
        "posts": posts,
        "coverage": {
            "source": "Bluesky",
            "posts_analyzed": post_count,
            "unique_authors": len(authors),
        },
    }


def get_contract_party(candidate):
    candidate = (candidate or "").strip().lower()
    if "democratic" in candidate:
        return "Democrat"
    if "republican" in candidate:
        return "Republican"
    return CANDIDATE_PARTIES.get(candidate, "")


@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/event/<event_ticker>")
def event(event_ticker):
    return render_template("event.html")


@app.get("/api/events")
def events_api():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM market ORDER BY event_ticker").fetchall()

    grouped = {}
    for row in rows:
        event_ticker = row["event_ticker"]
        if event_ticker not in grouped:
            grouped[event_ticker] = []
        grouped[event_ticker].append(row)

    events = []
    for event_ticker, contracts in grouped.items():
        events.append(get_event(event_ticker, contracts))
    events.sort(key=lambda event: event["volume"], reverse=True)
    return jsonify({"events": events})


@app.get("/api/events/<event_ticker>")
def event_api(event_ticker):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM market WHERE event_ticker = ? ORDER BY volume DESC",
            (event_ticker,),
        ).fetchall()

    if not rows:
        abort(404, description="Kalshi event not found")

    return jsonify(get_event(event_ticker, rows))


@app.get("/api/events/<event_ticker>/social")
def event_social_api(event_ticker):
    social_data = load_social_data(event_ticker)

    if not social_data:
        abort(404, description="Social data not found")

    posts = social_data["posts"]

    with get_db() as conn:
        contracts = conn.execute(
            "SELECT ticker, candidate FROM market WHERE event_ticker = ?",
            (event_ticker,),
        ).fetchall()

    predictions = {}
    for post in posts:
        party = post["supported_party"]
        predictions[party] = predictions.get(party, 0) + 1

    total = len(posts)

    contract_predictions = []
    for contract in contracts:
        party = get_contract_party(contract["candidate"])

        post_count = predictions.get(party, 0)
        probability = None
        if party and total:
            probability = round(post_count / total * 100)

        contract_predictions.append({
            "ticker": contract["ticker"],
            "party": party,
            "predictive_posts": post_count,
            "social_probability": probability,
        })

    return jsonify({
        "directional_prediction_count": total,
        "predictions": predictions,
        "contract_predictions": contract_predictions,
        "coverage": social_data["coverage"],
    })


@app.get("/api/events/<event_ticker>/social/posts")
def event_social_posts_api(event_ticker):
    social_data = load_social_data(event_ticker)

    if not social_data:
        abort(404, description="Social posts not found")

    posts = social_data["posts"]

    posts.sort(key=lambda post: post["like_count"], reverse=True)
    return jsonify({"posts": posts[:20]})

if __name__ == "__main__":
    app.run(debug=True)
