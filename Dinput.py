import os
os.environ["DATABASE_URL"] = "postgresql://daaatabase_user:c4aJ0oxLn0H1WbtvnaIIfpFtwojt4lps@dpg-d984p8mrnols73emqqbg-a.oregon-postgres.render.com/daaatabase"

from dotenv import load_dotenv
load_dotenv()

import subprocess
subprocess.run(["python", "-u", "api/kalshi_ingest.py"])