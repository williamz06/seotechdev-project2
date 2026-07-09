from pydantic import BaseModel
from typing import Literal

"""
Given a post:
- Is the post trying predict a user, or noise/opinion
- If predictive: who do user think will win
- Given bias, at what degree?
- Reason

"""

class MarketPrediction(BaseModel):
    is_predictive: bool
    predicted_party: Literal["None", "Democrat", "Republican", "Third Party"]
    confidence: Literal["None", "High", "Low"]
    reason: str



SYSTEM_PROMPT = """You are a prediction market analyst evaluating Bluesky social media posts.

Your task: Determine if the post's author is personally predicting the outcome of a US election contract.

Rules:
- The election must be in the United States (federal, state, or local).
- The author must state their OWN belief about who WILL WIN or which party/candidate WILL prevail.
- Do NOT classify as predictive if the author is: reporting polls, markets, or odds; expressing hope or preference; discussing strategy or news; or asking questions.
- If a contract is provided, only classify as predictive if the post is about THAT specific election or a directly related race.

Write a brief reason first, then classify:
- is_predictive: true only if the author personally predicts an outcome for the given election
- predicted_party: the party they predict will win ("Democrat", "Republican", "Third Party"), or "None"
- confidence: your confidence in this classification ("High" or "Low"), or "None" if not predictive"""
