import os
import sqlite3
from datetime import datetime, timezone

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2
    import psycopg2.extras

    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'markets.db')


def get_conn() -> sqlite3.Connection:
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_tables():
    if USE_POSTGRES:
        with get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bluesky_post (
                    uri           TEXT PRIMARY KEY,
                    cid           TEXT,
                    author_handle TEXT,
                    author_did    TEXT,
                    text          TEXT,
                    created_at    TEXT,
                    indexed_at    TEXT,
                    langs         TEXT,
                    like_count    INTEGER DEFAULT 0,
                    repost_count  INTEGER DEFAULT 0,
                    reply_count   INTEGER DEFAULT 0,
                    quote_count   INTEGER DEFAULT 0,
                    source_query  TEXT,
                    query_team    TEXT,
                    event_id      TEXT,
                    fetched_at    TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS post_prediction (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    uri             TEXT REFERENCES bluesky_post(uri),
                    event_id        TEXT,
                    is_predictive   INTEGER,
                    predicted_party TEXT,
                    confidence      TEXT,
                    reason          TEXT,
                    classified_at   TEXT
                )
            """)
    else:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bluesky_post (
                    uri           TEXT PRIMARY KEY,
                    cid           TEXT,
                    author_handle TEXT,
                    author_did    TEXT,
                    text          TEXT,
                    created_at    TEXT,
                    indexed_at    TEXT,
                    langs         TEXT,
                    like_count    INTEGER DEFAULT 0,
                    repost_count  INTEGER DEFAULT 0,
                    reply_count   INTEGER DEFAULT 0,
                    quote_count   INTEGER DEFAULT 0,
                    source_query  TEXT,
                    query_team    TEXT,
                    event_id      TEXT,
                    fetched_at    TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS post_prediction (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    uri             TEXT REFERENCES bluesky_post(uri),
                    event_id        TEXT,
                    is_predictive   INTEGER,
                    predicted_party TEXT,
                    confidence      TEXT,
                    reason          TEXT,
                    classified_at   TEXT
                )
            """)
            try:
                cur.execute("ALTER TABLE post_prediction ADD COLUMN event_id TEXT")
            except Exception:
                pass
            conn.commit()
        finally:
            conn.close()


def upsert_bluesky_posts(rows: list[dict], event_id: str):
    """Insert new posts; skip duplicates on URI."""
    now = datetime.now(timezone.utc).isoformat()
    records = [{**row, "event_id": event_id, "fetched_at": now} for row in rows]
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.executemany(
                """
                INSERT INTO bluesky_post
                    (uri, cid, author_handle, author_did, text, created_at, indexed_at,
                     langs, like_count, repost_count, reply_count, quote_count,
                     source_query, query_team, event_id, fetched_at)
                VALUES
                    (%(uri)s, %(cid)s, %(author_handle)s, %(author_did)s, %(text)s, %(created_at)s, %(indexed_at)s,
                     %(langs)s, %(like_count)s, %(repost_count)s, %(reply_count)s, %(quote_count)s,
                     %(source_query)s, %(query_team)s, %(event_id)s, %(fetched_at)s)
                ON CONFLICT (uri) DO NOTHING
                """,
                records,
            )
        else:
            cur.executemany(
                """
                INSERT OR IGNORE INTO bluesky_post
                    (uri, cid, author_handle, author_did, text, created_at, indexed_at,
                     langs, like_count, repost_count, reply_count, quote_count,
                     source_query, query_team, event_id, fetched_at)
                VALUES
                    (:uri, :cid, :author_handle, :author_did, :text, :created_at, :indexed_at,
                     :langs, :like_count, :repost_count, :reply_count, :quote_count,
                     :source_query, :query_team, :event_id, :fetched_at)
                """,
                records,
            )
        conn.commit()
    finally:
        conn.close()


def insert_predictions(predictions: list[dict], event_id: str):
    """Append classification results tagged with the Kalshi event_id."""
    now = datetime.now(timezone.utc).isoformat()
    records = [{**p, "event_id": event_id, "classified_at": now} for p in predictions]
    conn = get_conn()
    try:
        cur = conn.cursor()
        if USE_POSTGRES:
            cur.executemany(
                """
                INSERT INTO post_prediction
                    (uri, event_id, is_predictive, predicted_party, confidence, reason, classified_at)
                VALUES
                    (%(uri)s, %(event_id)s, %(is_predictive)s, %(predicted_party)s, %(confidence)s, %(reason)s, %(classified_at)s)
                """,
                records,
            )
        else:
            cur.executemany(
                """
                INSERT INTO post_prediction
                    (uri, event_id, is_predictive, predicted_party, confidence, reason, classified_at)
                VALUES
                    (:uri, :event_id, :is_predictive, :predicted_party, :confidence, :reason, :classified_at)
                """,
                records,
            )
        conn.commit()
    finally:
        conn.close()


def load_posts(event_id: str | None = None) -> list[dict]:
    """Return bluesky_post rows, optionally filtered by event_id."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        placeholder = "%s" if USE_POSTGRES else "?"
        if event_id:
            cur.execute(f"SELECT * FROM bluesky_post WHERE event_id = {placeholder}", (event_id,))
        else:
            cur.execute("SELECT * FROM bluesky_post")
        rows = cur.fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]
