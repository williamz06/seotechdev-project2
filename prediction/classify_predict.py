import pandas as pd
import ollama
from concurrent.futures import ThreadPoolExecutor, as_completed
from prediction.model_schema import MarketPrediction, SYSTEM_PROMPT

try:
    from api.db import init_tables, insert_predictions
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from api.db import init_tables, insert_predictions

BLUESKY_POSTS = 'BLUESKY_POSTS_US_PREZ_2028_BASELINE.csv'
MODEL_NAME = "qwen2.5:0.5b"
MAX_WORKERS = 8


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
    if langs and 'en' not in langs:
        return {"uri": row['uri'], "is_predictive": False, "predicted_party": "None", "confidence": "None", "reason": "non-english"}

    try:
        result = classify_post(row['text'])
        return {
            "uri": row['uri'],
            "is_predictive": result.is_predictive,
            "predicted_party": result.predicted_party,
            "confidence": result.confidence,
            "reason": result.reason
        }
    except Exception as e:
        print(f"Error classifying {row['uri']}: {e}")
        return {"uri": row['uri'], "is_predictive": False, "predicted_party": "None", "confidence": "None", "reason": ""}


def main():
    df = pd.read_csv(BLUESKY_POSTS)
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
                print(f"Post Text: {row['text']}\n"
                      f"  Prediction Found: {result['predicted_party']}\n"
                      f"  Confidence: {result['confidence']}\n"
                      f"  Reason: {result['reason']}\n")

            if completed % 500 == 0:
                print(f"Progress: {completed}/{len(rows)}")

    if not results:
        print("THIS THING DO NOT WORK! CHECK PREDICTION")
        return

    results_df = pd.DataFrame(results)
    final_df = df.merge(results_df, on="uri")
    final_df['needs_review'] = final_df['confidence'] == 'Low'
    final_df.to_csv("classified_predictions.csv", index=False)
    predictive_count = final_df['is_predictive'].sum()
    print(f"\nDone. {predictive_count}/{len(final_df)} posts classified as predictive.")
    print(f"Output: classified_predictions.csv")

    init_tables()
    insert_predictions(results)
    print(f"Saved {len(results)} predictions to markets.db (post_prediction table)")

    compute_implied_probability(final_df)


def compute_implied_probability(df: pd.DataFrame) -> dict:
    predictive = df[df['is_predictive'] == True]
    dem   = (predictive['predicted_party'] == 'Democrat').sum()
    rep   = (predictive['predicted_party'] == 'Republican').sum()
    third = (predictive['predicted_party'] == 'Third Party').sum()
    total = dem + rep + third

    if total == 0:
        print("\nNo predictive posts found — cannot compute implied probability.")
        return {}

    probs = {
        'Democrat':    round(dem / total, 4),
        'Republican':  round(rep / total, 4),
        'Third Party': round(third / total, 4),
    }

    print("\n--- Bluesky Implied Probability ---")
    print(f"  Democrat:    {probs['Democrat']:.1%}  ({dem} posts)")
    print(f"  Republican:  {probs['Republican']:.1%}  ({rep} posts)")
    print(f"  Third Party: {probs['Third Party']:.1%}  ({third} posts)")
    print(f"  Total predictive posts: {total}")
    return probs


if __name__ == "__main__":
    main()