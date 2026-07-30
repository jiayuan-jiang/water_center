"""
Sentiment + emotion analysis per document, aggregated per topic.
Input:  data/topics/documents_with_topics.csv        (reddit, default)
        data/topics_bluesky/documents_with_topics.csv (bluesky)
Output: data/analysis/sentiment_docs_{platform}.csv
        data/analysis/sentiment_by_topic_{platform}.csv

Reddit only: also joins in Reddit's own per-comment `controversiality` flag
(present in data/comments_raw.jsonl, dropped during preprocess.py) as a
platform-sourced complement to our own sentiment-based controversy_score —
see spec/controversy-score.md.

Usage:
    python sentiment_analysis.py                   # Reddit
    python sentiment_analysis.py --platform bluesky
"""

import argparse
import json
import os
import pandas as pd
import torch
from pathlib import Path
from transformers import pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--platform", choices=["reddit", "bluesky"], default="reddit")
parser.add_argument("--batch-size", type=int, default=64)
args = parser.parse_args()

# ── Platform config ───────────────────────────────────────────────────────────
if args.platform == "bluesky":
    DOCS_FILE = Path("data/topics_bluesky/documents_with_topics.csv")
    # Only the 28 labeled valid-signal topics (same set as subtopic_model.py)
    VALID_TOPICS = {
        0, 1, 4, 5, 10, 13, 15, 18, 19, 26, 27, 28, 29, 31,
        32, 33, 35, 36, 39, 41, 43, 45, 46, 48, 49, 50, 53, 59,
    }
else:
    DOCS_FILE = Path("data/topics/documents_with_topics.csv")
    VALID_TOPICS = None  # all 34 topics are labeled; only -1 is excluded

OUT_DIR = Path("data/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCS_OUT = OUT_DIR / f"sentiment_docs_{args.platform}.csv"
TOPIC_OUT = OUT_DIR / f"sentiment_by_topic_{args.platform}.csv"

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment"
EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"
SENTIMENT_LABEL_MAP = {"LABEL_0": "negative", "LABEL_1": "neutral", "LABEL_2": "positive"}

if torch.cuda.is_available():
    DEVICE = 0
elif torch.backends.mps.is_available():
    DEVICE = "mps"  # requires explicit max_length below — MPS's SDPA kernel
                     # overflows ("Invalid buffer size") on untruncated sequences
else:
    DEVICE = -1
    torch.set_num_threads(os.cpu_count())


def load_reddit_controversiality():
    mapping = {}
    with open("data/comments_raw.jsonl") as f:
        for line in f:
            d = json.loads(line)
            mapping[d["id"]] = d.get("controversiality", 0)
    return mapping


def run_pipeline(pipe, texts, batch_size, tag):
    labels, scores = [], []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for result in pipe(batch, batch_size=batch_size, truncation=True, max_length=512, top_k=1):
            top = result[0] if isinstance(result, list) else result
            labels.append(top["label"])
            scores.append(top["score"])
        if (i // batch_size) % 20 == 0:
            print(f"  [{tag}] {min(i + batch_size, len(texts)):,}/{len(texts):,}")
    return labels, scores


def main():
    df = pd.read_csv(DOCS_FILE)
    df = df[df["topic"] != -1].copy()
    if VALID_TOPICS is not None:
        df = df[df["topic"].isin(VALID_TOPICS)].copy()
    df["text"] = df["text"].fillna("")
    print(f"Scoring {len(df):,} docs ({args.platform})")

    if args.platform == "reddit":
        controversiality = load_reddit_controversiality()
        df["reddit_controversiality"] = df["id"].map(controversiality).fillna(0).astype(int)

    sentiment_pipe = pipeline("text-classification", model=SENTIMENT_MODEL, device=DEVICE)
    emotion_pipe = pipeline("text-classification", model=EMOTION_MODEL, device=DEVICE)

    texts = df["text"].tolist()
    print("Sentiment...")
    sent_labels, sent_scores = run_pipeline(sentiment_pipe, texts, args.batch_size, "sentiment")
    df["sentiment"] = [SENTIMENT_LABEL_MAP.get(l, l) for l in sent_labels]
    df["sentiment_score"] = sent_scores

    print("Emotion...")
    emo_labels, emo_scores = run_pipeline(emotion_pipe, texts, args.batch_size, "emotion")
    df["emotion"] = emo_labels
    df["emotion_score"] = emo_scores

    doc_cols = ["id", "topic", "sentiment", "sentiment_score", "emotion", "emotion_score"]
    if args.platform == "reddit":
        doc_cols.append("reddit_controversiality")
    docs_out = df[doc_cols]
    docs_out.to_csv(DOCS_OUT, index=False)
    print(f"Written: {DOCS_OUT} ({len(docs_out):,} rows)")

    rows = []
    for topic, group in df.groupby("topic"):
        n = len(group)
        sent_pct = (group["sentiment"].value_counts(normalize=True) * 100).to_dict()
        pos_pct = sent_pct.get("positive", 0.0)
        neg_pct = sent_pct.get("negative", 0.0)
        neu_pct = sent_pct.get("neutral", 0.0)
        # Balance ratio in [0, 1]: 1 = perfectly split pos/neg, independent of
        # neutral mass. See spec/controversy-score.md for why this replaced
        # the earlier min(pos,neg)*2 formula, and for the opinion-mass floor
        # below (a 0.2%/0.2% split is "nobody has an opinion", not "perfectly
        # controversial" — caught via the weather-bot topics scoring 1.0).
        largest = max(pos_pct, neg_pct)
        opinion_mass = pos_pct + neg_pct
        if opinion_mass < 5.0 or largest == 0:
            controversy = 0.0
        else:
            controversy = min(pos_pct, neg_pct) / largest
        emo_pct = (group["emotion"].value_counts(normalize=True) * 100).to_dict()
        dominant_emotion = max(emo_pct, key=emo_pct.get)
        row = {
            "topic": topic,
            "n_docs": n,
            "pct_positive": round(pos_pct, 1),
            "pct_neutral": round(neu_pct, 1),
            "pct_negative": round(neg_pct, 1),
            "controversy_score": round(controversy, 3),
            "dominant_emotion": dominant_emotion,
            **{f"pct_emotion_{k}": round(v, 1) for k, v in emo_pct.items()},
        }
        if args.platform == "reddit":
            row["pct_reddit_controversial"] = round(group["reddit_controversiality"].mean() * 100, 1)
        rows.append(row)

    topic_out = pd.DataFrame(rows).sort_values("controversy_score", ascending=False)
    topic_out.to_csv(TOPIC_OUT, index=False)
    print(f"Written: {TOPIC_OUT} ({len(topic_out):,} topics)")


if __name__ == "__main__":
    main()
