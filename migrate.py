import os
import psycopg2

DATABASE_URL = "postgresql://daaatabase_user:c4aJ0oxLn0H1WbtvnaIIfpFtwojt4lps@dpg-d984p8mrnols73emqqbg-a.oregon-postgres.render.com/daaatabase"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("ALTER TABLE market ADD COLUMN IF NOT EXISTS url TEXT")
conn.commit()
conn.close()
print("done")