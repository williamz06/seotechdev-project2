import pandas as pd
import ollama
from concurrent.futures import ThreadPoolExecutor, as_completed
from model_schema import MarketPrediction, SYSTEM_PROMPT

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


if __name__ == "__main__":
    main()