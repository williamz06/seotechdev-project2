from flask import Flask, render_template, jsonify
from api.db import get_dashboard_predictions, init_tables
app = Flask(__name__)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/event/<event_id>")
def event(event_id):
    return render_template("event.html", event_id=event_id)
@app.route("/api/posts/event/<event_id>")
def api_event_posts(event_id):
    try: 
        data = get_dashboard_predictions(event_id=event_id)
        return jsonify(data)
    except Exception as e: 
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    init_tables()
    app.run(debug=True)
