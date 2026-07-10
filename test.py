import os
os.environ["DATABASE_URL"] = "postgresql://daaatabase_user:c4aJ0oxLn0H1WbtvnaIIfpFtwojt4lps@dpg-d984p8mrnols73emqqbg-a.oregon-postgres.render.com/daaatabase"

from dotenv import load_dotenv
load_dotenv()

print("1. Testing Kalshi API...", flush=True)
import requests
r = requests.get("https://external-api.kalshi.com/trade-api/v2/series", params={"tags": "US Elections"}, timeout=15)
print(f"   Kalshi responded: {r.status_code}, {len(r.json()['series'])} series found", flush=True)

print("2. Testing Bluesky login...", flush=True)
from atproto import Client
client = Client()
client.login(os.getenv("BLUESKY_USERNAME"), os.getenv("BLUESKY_PASSWORD"))
print("   Bluesky login succeeded", flush=True)

print("All good.", flush=True)