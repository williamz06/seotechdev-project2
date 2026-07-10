# seotechdev-project2

## /API

### Kalshi API (@Will)

Fetches prediction market contracts from Kalshi with a given tag (in-scope: Binary US Elections)

1. Calls get_series_list(tags="US Elections") to get all US election series
2. For each series, calls get_markets() to get individual contracts with a given `eventID`
3. Filter to binary contracts using is_eligible_contract():
- Drop over/under contracts
- Drop numeric contracts
- Keep winner-prediction using *ReGex* -- "win", "elected", "presidents" etc,..
4. Take top 100 by volume, upsert into MARKET and PRICE_HISTORY table

-- Tested with *argparse* 
`python api/kalshi_ingest.py --url https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028`

### BlueSky API

Fetches blueSky posts that are relevant to a given Kalshi Event.

1. Receives config from **kalshi_ingest.py**
- event_id (e.g. Kalshi's ticker : `KXPRESPARTY_2028`)
- kickoff (fixed time window)
- window_pad_min (how far back/forward to search)
- market_queries (general key words from Kalshi's title, description)
    - Contraint: we used a dictionary to match certain keywords to queries
    - Hence, we can narrow down keywords according to a contract's title. 
    - e.g. Contract is about 2028 Presidential Election Party Winner, then we would infer that any mention of Hillary, Harris, Biden would infer about Democrat. This helps with classification later on using Qwen.

2. BlueSky Auth
3. Searches keywords, and paginate up to 5000 posts per query with a delay in-between
4. Deduplicate multiple results by *uri* so that same post can lead to many eventIDs
5. Saves to CSV
6. Writes to DB 

## /Prediction -- meant to be run locally, not hosted due to costs

Reads fetched posts and use local LLM (ollama Qwen2.5:0.5) to determine if each post is making an event prediction.

Why did we use a local LLM instead of API calls?
- Cheaper to run text classification over thousands of posts than an AI API call.
- Running a classification ML model and sentiment analysis is infeasible given our time constraint, 
lack of training data for broad prediction market sentiment, and would require fine-tuning to justify a better accuracy than a light-weight LLM. 
-  We use ThreadPoolExecutor instead of ProcessPoolExecutor because Ollama runs Qwen in a container, so the python process is making HTTP requests to the container to query and get response -- I/O-bound. 


1. Runs `--all` (all CSVs) or `--input`
2. deriver event_id from file_name (in the future, would cross-check db)
3. For each post, classify post by:
- Inject text to master-prompt in JSON to Ollama 
- Gets back JSON response enforce by MarketPrediction Pydantic schema
- Return (0/1) is_predictive, predicted_party, confidence and reason (for exploratory)
4. Runs 8 workers (ThreadPoolExecutor) for speed -- sequential was taking too long
- This depends on your hardware
- TLDR: each thread is intiated with its own cores from the system's CPU. An internal queue is set-up for process each post, popping and appending the next post. This helps reduce the initiation overhead from sequentially running a process. 

5. Skip non-English posts 
6. Save to CSV and write to DB

Example Run
``` 

python -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

ollama pull qwen2.5:0.5b (~499 MB)

python api/kalshi_ingest.py --url "https://kalshi.com/markets/kxpresparty/party-winning-presidency/kxpresparty-2028" 

python prediction/classify_predict.py --all

```