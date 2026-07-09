"""
Fetch Bluesky posts for a single match

Env:   BLUESKY_USERNAME, BLUESKY_PASSWORD in a .env file
"""

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from atproto import Client
from dotenv import load_dotenv

try:
    from api.db import init_tables, upsert_bluesky_posts
except ImportError:
    from db import init_tables, upsert_bluesky_posts

# Standardize BlueSky Errors
try:
    from atproto.exceptions import NetworkError, InvokeTimeoutError, AtProtocolError
    RETRYABLE = (NetworkError, InvokeTimeoutError, AtProtocolError)
except Exception:
    RETRYABLE = (Exception,)


EVENT_ID = "US_PREZ_2028_BASELINE"

# Kickoff time stamp 
# Bounded Window for a given game to filter pre and post match
KICKOFF = datetime(2026, 7, 6, 19, 0, tzinfo=timezone.utc)
MATCH_MINUTES =  120
WINDOW_PAD_MIN = 30 # buffer

# Matching keywords in posts
MARKET_QUERIES = [
    "2028 election", "2028 presidential", "next president 2028",
    "polymarket election", "election contract"
]
OPTIONS_QUERIES = {
    "democrat": [
        "Democrats", "Democrat", "DNC", "Blue wave", 
        "Harris", "Newsom", "Shapiro" # Adapts as candidates emerge
    ],
    "republican": [
        "Republicans", "Republican", "GOP", "Red wave", "MAGA",
        "Vance", "DeSantis", "Trump 2028"
    ],
    "third_party": [
        "Third party", "Libertarian", "Green party", "RFK Jr"
    ]
}

RESOLUTION_QUERIES = [
    "election resolution", "associated press call", "fox news call", 
    "nbc call", "inauguration date", "january 20 2029"
]


MAX_POSTS_PER_QUERY = 5000

PAGE_SLEEP_SEC = 0.5 # prevent timeout
OUTPUT_CSV = f"BLUESKY_POSTS_{EVENT_ID}.csv"

def iso_z(dt):
    """
    RFC3339 timestamp Bluesky accepts, e.g. 2026-07-06T18:30:00Z
    """
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def flatten_post(post, source_query, team):
    """
    Pull only the fields later stages need out of a PostView object
    """

    rec = post.record
    langs = getattr(rec, "langs", None) or []

    return {
        "uri": post.uri,
        "cid": post.cid,
        "author_handle": post.author.handle,
        "author_did": post.author.did,
        "text": (getattr(rec, "text", "") or "").replace("\n", " ").strip(),
        "created_at": getattr(rec, "created_at", None),   # when the user posted
        "indexed_at": getattr(post, "indexed_at", None),  # when Bluesky saw it
        "langs": ",".join(langs),
        "like_count": getattr(post, "like_count", 0) or 0,
        "repost_count": getattr(post, "repost_count", 0) or 0,
        "reply_count": getattr(post, "reply_count", 0) or 0,
        "quote_count": getattr(post, "quote_count", 0) or 0,
        "source_query": source_query,
        "query_team": team or "",   # NOT stance; just which query found it
    }

def search_all_pages(client, query, since, until, max_posts):
    """
    Paginate search_posts for one query
    Return PostViews
    """

    collected = []
    cursor = None
    fails = 0
    while True:
        params = {
            "q": query,
            "limit" : 100,      # MAX LIMIT PER CALL
            "sort"  : "latest",  # Chronological
            "since" : since,
            "until" : until,
        }
        if cursor:
            params["cursor"] = cursor
        try:   
            resp    = client.app.bsky.feed.search_posts(params)
            fails   = 0
        
        # happens when timeout + too many requests , then retry

        except RETRYABLE as e:
            fails += 1

            if fails >= 4:
                print(f"    giving up on '{query}' after repeated errors: {e}")
                break
            wait = 2 ** fails

            print(f"    error on '{query}' ({e}); backing off {wait}s")
            time.sleep(wait)
            continue

        # add to total posts and move cursor.next
        collected.extend(resp.posts)
        cursor = resp.cursor

        if not cursor or len(collected) >= max_posts:
            break
        time.sleep(PAGE_SLEEP_SEC)

    return collected

def main():
    load_dotenv()
    client = Client()
    client.login(os.getenv("BLUESKY_USERNAME"), os.getenv("BLUESKY_PASSWORD"))

    # Window
    since = iso_z(KICKOFF - timedelta(minutes = WINDOW_PAD_MIN))
    until = iso_z(KICKOFF + timedelta(minutes=MATCH_MINUTES + WINDOW_PAD_MIN))
    print(f"Match window (indexed-time filter): {since} -> {until}")
    
    # Query Match, Teams
    plan = []
    for q in MARKET_QUERIES:
        plan.append((q, "macro_market"))
    for q in RESOLUTION_QUERIES:
        plan.append((q, "resolution_clause"))
    for category, queries in OPTIONS_QUERIES.items():
        for q in queries:
            plan.append((q, f"party_{category}"))
    
    rows_by_uri = {}

    for query, team in plan:
        label = team or "match"
        print(f"Searching [{label}] '{query}' ....")

        posts = search_all_pages(client, query, since, until, MAX_POSTS_PER_QUERY)

        for p in posts:
            row = flatten_post(p, query, team)
            rows_by_uri.setdefault(row["uri"], row) 

        print(f" {len(posts)} fetched, {len(rows_by_uri)} unique so far :O")

    rows = list(rows_by_uri.values())
    if not rows:
        print("No Posts found! Redo window or match keywords")

        return
    
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote {len(df)} unique posts to {OUTPUT_CSV}")
    print(f"Columns: {list(df.columns)}")
    print(f"Sample: @{rows[0]['author_handle']}: {rows[0]['text'][:80]}")

    init_tables()
    upsert_bluesky_posts(rows, EVENT_ID)
    print(f"Saved {len(rows)} posts to markets.db (bluesky_post table)")
 
 
if __name__ == "__main__":
    main()