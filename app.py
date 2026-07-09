import os
import sqlite3

from flask import Flask, abort, jsonify, render_template

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api", "markets.db")


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
    is_open = False

    for row in rows:
        contract = get_contract(row)
        contracts.append(contract)
        total_volume += contract["volume"] or 0

        if contract["status"] == "open":
            is_open = True
        if contract["observed_at"] and (not last_updated or contract["observed_at"] > last_updated):
            last_updated = contract["observed_at"]

    contracts.sort(key=lambda contract: contract["volume"] or 0, reverse=True)

    return {
        "event_ticker": event_ticker,
        "display_name": event_ticker,
        "platform": "Kalshi",
        "contract_count": len(contracts),
        "status": "open" if is_open else contracts[0]["status"],
        "volume": total_volume,
        "last_updated": last_updated,
        "contracts": contracts,
    }

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

if __name__ == "__main__":
    app.run(debug=True)
