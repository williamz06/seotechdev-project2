import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'markets.db')


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_tables():
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
                is_predictive   INTEGER,
                predicted_party TEXT,
                confidence      TEXT,
                reason          TEXT,
                classified_at   TEXT
            )
        """)
        conn.commit()


def upsert_bluesky_posts(rows: list[dict], event_id: str):
    """Insert new posts; skip duplicates on URI."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.executemany(
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
            [{**row, "event_id": event_id, "fetched_at": now} for row in rows],
        )
        conn.commit()


def insert_predictions(predictions: list[dict]):
    """Append classification results;"""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO post_prediction
                (uri, is_predictive, predicted_party, confidence, reason, classified_at)
            VALUES
                (:uri, :is_predictive, :predicted_party, :confidence, :reason, :classified_at)
            """,
            [{**p, "classified_at": now} for p in predictions],
        )
        conn.commit()


def load_posts(event_id: str | None = None) -> list[dict]:
    """Return bluesky_post rows, optionally filtered by event_id."""
    with get_conn() as conn:
        if event_id:
            rows = conn.execute(
                "SELECT * FROM bluesky_post WHERE event_id = ?", (event_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM bluesky_post").fetchall()
    return [dict(r) for r in rows]
