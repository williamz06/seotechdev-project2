from flask import Flask, jsonify
import praw
import os
from dotenv import load_dotenv

load_dotenv()
# https://github.com/nama1arpit/reddit-streaming-pipeline

# IF PRAW permissions exist
app = Flask(__name__)

# Reddit Auth
reddit = praw.Reddit(
    client_id       = os.getenv("REDDIT_CLIENT_ID")
    , client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    , user_agent    = os.getenv("REDDIT_USER_AGENT")
)

@app.route('/api/posts/{subreddit_name}', method=['GET'])
def get_reddit_posts(subreddit_name):
    try:
        subreddit  = reddit.subreddit(subreddit_name)
        posts_data = []

        # Get top k posts
        for post in subreddit.hot(limit = 5) :
            posts_data.append({
                'title' : post.title,
                'author': str(post.author),
                'score' : post.score,
                'url'  : post.url,
                'num_comments' : post.num_comments
            })

        
        return jsonify({
            'status'    : 'success',
            'subreddit' : subreddit_name,
            'posts'     : posts_data
        }), 200
    
    except Exception as e:
        # SubReddit don't exist, API fails, etc,..
        return jsonify({
            'status'  : 'error',
            'message' : str(e)
        }), 500
    
