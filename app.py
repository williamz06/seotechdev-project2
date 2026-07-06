from flask import Flask, jsonify
import praw

app = Flask(__name__)

# Reddit Auth
reddit = praw.Reddit()