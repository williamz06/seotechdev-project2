import os
os.environ["DATABASE_URL"] = "postgresql://daaatabase_user:c4aJ0oxLn0H1WbtvnaIIfpFtwojt4lps@dpg-d984p8mrnols73emqqbg-a.oregon-postgres.render.com/daaatabase"
os.environ["BLUESKY_USERNAME"] = "ccramir.bsky.social"
os.environ["BLUESKY_PASSWORD"] = "d7ua-hyg6-kkzq-bquk"

import subprocess
subprocess.run([
    "python", "api/kalshi_ingest.py",
    "--url", "https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028"
])