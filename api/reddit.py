"""
Using public JSON endpoints

From a given subrreddit endpoint:
https://www.reddit.com/r/worldcup/top.json?t=week&limit=50

for each post with ID post_id, fetch comments:
https://www.reddit.com/r/worldcup/comments/{post_id}/top.json
https://www.reddit.com/r/worldcup/comments/{post_id}/hot.json

"""

import requests
import pandas as pd

REDDIT_USERNAME = 'swavrobski_minion'

def get_comments(post_id, redditThread = 'worldcup', sort = 'top'):
    url     = f"https://www.reddit.com/r/{redditThread}/comments/{post_id}/{sort}.json"
    headers = {"Accept": "application/json",
               "User-Agent": f"my-worldcup_sentiment/1.0 (by /u/{REDDIT_USERNAME})"} 
    response = requests.get(url, headers = headers)
    data     = response.json()
    
    if len(data) < 2:
        return []
    
    comments_data = data[1]["data"]["children"]
    comments = []

    def process(comment, depth = 0):
        if comment["kind"] != "comment":
            return
        c = comment["data"]
        comments.append({
            "comment_body"          : c["body"],
            "comment_score"         : c["score"],
            "comment_author"        : c["author"],
            "comment_created_utc"   : c["created_utc"],
            "depth"                 : depth,
            "parent_id"             : c["parent_id"]
        })
        # Recurse for nested comments
        for child in c.get("replies", []):
            if isinstance(child, dict):
                process(child, depth + 1)
    
    for node in comments_data:
        if node["kind"] == "comment":
            process(node, depth = 0)
    
    return comments

posts_url = "https://www.reddit.com/r/worldcup/top.json"
params = {"t": "week", "limit": 10}
posts_resp = requests.get(posts_url, params=params, headers={"Accept": "application/json"})
posts_data = posts_resp.json()

records = []
for p in posts_data["data"]["children"]:
    post        = p["data"]
    post_id     = post["id"]
    post_title  = post["title"]
    comments    = get_comments(post_id, sort="top")
    for c in comments:
        records.append({
            "post_id": post_id,
            "post_title": post_title,
            **c
        })

df = pd.DataFrame(records)

if __name__ == '__main__':
    print(df.head())
