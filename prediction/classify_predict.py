"""
python -m prediction.classify_predict --all
"""

import os
import re
import glob
import argparse
import pandas as pd
import ollama
from concurrent.futures import ThreadPoolExecutor, as_completed
from prediction.model_schema import MarketPrediction, SYSTEM_PROMPT

try:
    from api.db import init_tables, insert_predictions
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from api.db import init_tables, insert_predictions

BLUESKY_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'api', 'bluesky_output')
MODEL_NAME = "qwen2.5:0.5b"
MAX_WORKERS = 8


def extract_event_id(filepath: str) -> str:
    """BLUESKY_POSTS_KXPRESPARTY_2028.csv → KXPRESPARTY_2028"""
    name = os.path.basename(filepath)
    name = re.sub(r'\.csv$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'^BLUESKY_POSTS_', '', name)
    return name


def classify_post(post_text: str) -> MarketPrediction:
    response = ollama.chat(
        model=MODEL_NAME,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': f"Classify this post: '{post_text}'"}
        ],
        format=MarketPrediction.model_json_schema(),
        options={'temperature': 0}
    )
    return MarketPrediction.model_validate_json(response['message']['content'])


def process_row(row):
    langs = str(row.get('langs', 'en') or 'en')
    if 'en' not in langs:
        return {"uri": row['uri'], "is_predictive": False, "predicted_party": "None", "confidence": "None", "reason": "non-english"}
    try:
        result = classify_post(row['text'])
        return {
            "uri":             row['uri'],
            "is_predictive":   result.is_predictive,
            "predicted_party": result.predicted_party,
            "confidence":      result.confidence,
            "reason":          result.reason,
        }
    except Exception as e:
        print(f"Error classifying {row['uri']}: {e}")
        return {"uri": row['uri'], "is_predictive": False, "predicted_party": "None", "confidence": "None", "reason": ""}


def run(filepath: str):
    event_id = extract_event_id(filepath)
    print(f"\n=== {event_id} ({os.path.basename(filepath)}) ===")

    df = pd.read_csv(filepath)
    rows = df.to_dict('records')
    print(f"Classifying {len(rows)} posts with {MAX_WORKERS} workers...")

    results = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_row, row): row for row in rows}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1

            if result['is_predictive']:
                row = futures[future]
                print(f"  [{event_id}] {result['predicted_party']} | {result['confidence']} | {row['text'][:80]}")

            if completed % 500 == 0:
                print(f"  Progress: {completed}/{len(rows)}")

    if not results:
        print("No results — check model and input file.")
        return

    results_df = pd.DataFrame(results)
    final_df   = df.merge(results_df, on="uri")
    final_df['event_id']     = event_id
    final_df['needs_review'] = final_df['confidence'] == 'Low'

    out_csv = f"classified_{event_id}.csv"
    final_df.to_csv(out_csv, index=False)

    insert_predictions(results, event_id)

    predictive_count = final_df['is_predictive'].sum()
    print(f"Done: {predictive_count}/{len(final_df)} predictive  →  {out_csv}  |  saved to markets.db")

    compute_implied_probability(final_df, event_id)


def compute_implied_probability(df: pd.DataFrame, event_id: str = "") -> dict:
    predictive = df[df['is_predictive'] == True]
    dem   = (predictive['predicted_party'] == 'Democrat').sum()
    rep   = (predictive['predicted_party'] == 'Republican').sum()
    third = (predictive['predicted_party'] == 'Third Party').sum()
    total = dem + rep + third

    if total == 0:
        print("  No predictive posts — cannot compute implied probability.")
        return {}

    probs = {
        'Democrat':    round(dem / total, 4),
        'Republican':  round(rep / total, 4),
        'Third Party': round(third / total, 4),
    }

    label = f"[{event_id}] " if event_id else ""
    print(f"\n  {label}Bluesky Implied Probability")
    print(f"    Democrat:    {probs['Democrat']:.1%}  ({dem})")
    print(f"    Republican:  {probs['Republican']:.1%}  ({rep})")
    print(f"    Third Party: {probs['Third Party']:.1%}  ({third})")
    print(f"    Total predictive: {total}")
    return probs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify Bluesky posts per Kalshi event contract")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--input", help="Path to a single BLUESKY_POSTS_*.csv file")
    group.add_argument("--all",   action="store_true", help="Process every CSV in api/bluesky_output/")
    args = parser.parse_args()

    init_tables()

    if args.all:
        files = sorted(glob.glob(os.path.join(BLUESKY_OUTPUT_DIR, "BLUESKY_POSTS_*.csv")))
        if not files:
            print(f"No CSV files found in {BLUESKY_OUTPUT_DIR}")
        for f in files:
            run(f)
    elif args.input:
        run(args.input)
    else:
        # default: first CSV in bluesky_output, or explicit path
        parser.print_help()
