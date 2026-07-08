from atproto import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client()
client.login(os.getenv('BLUESKY_USERNAME'), os.getenv('BLUESKY_PASSWORD') )

# Define target URL
handle      = 'surfsports.bsky.social'
feed_name   = '2026-fifa-wor' 

# User's DID
identify = client.com.atproto.identity.resolve_handle({'handle': handle})
did      = identify.did

# construct URL for feed
feed_url = f"at://{did}/app.bsky.feed.generator/{feed_name}"

all_posts = []
cursor = None
print(f"Fetching posts from feed: {feed_name}...")


while True:
    try:
        response = client.app.bsky.feed.get_feed({
            'feed' : feed_url,
            'limit' : 10,
            'cursor' : cursor
        })

        all_posts.extend(response.feed)

        cursor = response.cursor
        print(f"Fetched {len(all_posts)} posts so far...")

        # reached the end of feed
        if not cursor:
            break
    except EOFError as e:
        print("Got error: ", e)

print(f"\nDone! Total posts fetched: {len(all_posts)}")

if all_posts:
    first_post = all_posts[0].post
    print(f"First post text: {first_post.record.text}")
    