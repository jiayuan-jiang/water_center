"""
NMF sub-topic analysis within each main BERTopic topic.
Input:  data/topics/documents_with_topics.csv        (reddit, default)
        data/topics_bluesky/documents_with_topics.csv (bluesky)
Output: data/subtopics/overview.json
        data/subtopics/topic_{N:02d}.csv
        (or data/subtopics_bluesky/ for bluesky)

Usage:
    python subtopic_model.py                   # Reddit
    python subtopic_model.py --platform bluesky
"""

import argparse
import json
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import NMF

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon"], default="reddit")
args = parser.parse_args()

# ── Platform config ───────────────────────────────────────────────────────────
if args.platform == "bluesky":
    DOCS_FILE    = Path("data/topics_bluesky/documents_with_topics.csv")
    SUMMARY_FILE = Path("data/topics_bluesky/topic_summary.csv")
    OUT_DIR      = Path("data/subtopics_bluesky")
    SOURCE_COL   = "source"
    # Only the 28 labeled valid-signal topics
    VALID_TOPICS = {
        0, 1, 4, 5, 10, 13, 15, 18, 19, 26, 27, 28, 29, 31,
        32, 33, 35, 36, 39, 41, 43, 45, 46, 48, 49, 50, 53, 59,
    }
elif args.platform == "mastodon":
    DOCS_FILE    = Path("data/topics_mastodon/documents_with_topics.csv")
    SUMMARY_FILE = Path("data/topics_mastodon/topic_summary.csv")
    OUT_DIR      = Path("data/subtopics_mastodon")
    SOURCE_COL   = "source"
    # Only the 16 labeled valid-signal topics
    VALID_TOPICS = {0, 1, 2, 4, 5, 6, 8, 10, 11, 12, 14, 15, 17, 21, 22, 24}
else:
    DOCS_FILE    = Path("data/topics/documents_with_topics.csv")
    SUMMARY_FILE = Path("data/topics/topic_summary.csv")
    OUT_DIR      = Path("data/subtopics")
    SOURCE_COL   = "subreddit"
    VALID_TOPICS = None  # all non-outlier topics

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
MIN_DOCS    = 40
TOP_WORDS   = 10
N_REPR_DOCS = 3

DOMAIN_STOP = {
    # generic corpus noise
    "lake", "lakes", "great", "michigan", "water", "people",
    "like", "just", "don", "ve", "really", "lot", "think",
    "know", "going", "make", "good", "said", "year", "years",
    # URL / link fragments (Bluesky share previews)
    "com", "org", "www", "http", "https", "arti", "article",
    "buff", "ly", "bsky", "social", "bsky social",
    # NOAA / weather bot formatting tokens
    "edt", "cdt", "pm", "am", "kts", "kt", "nm", "5nm",
    "oversized", "186", "185",
}
STOP_WORDS = list(ENGLISH_STOP_WORDS | DOMAIN_STOP)

IMBALANCE_RATIO = 5


def auto_k(n_docs: int) -> int:
    """One sub-topic per ~80 docs, clamped to [2, 6]."""
    return max(2, min(6, n_docs // 80))


# ── Load data ─────────────────────────────────────────────────────────────────
df      = pd.read_csv(DOCS_FILE)
summary = pd.read_csv(SUMMARY_FILE).set_index("Topic")

all_topic_ids = sorted(df[df["topic"] != -1]["topic"].unique())
topic_ids = [t for t in all_topic_ids if VALID_TOPICS is None or t in VALID_TOPICS]

print(f"Platform: {args.platform}  |  topics to process: {len(topic_ids)}")

# ── Main loop ─────────────────────────────────────────────────────────────────
overview = []

for tid in topic_ids:
    sub_df = df[df["topic"] == tid].copy().reset_index(drop=True)
    n      = len(sub_df)

    topic_name = summary.loc[tid, "Name"] if tid in summary.index else str(tid)

    if n < MIN_DOCS:
        print(f"Topic {tid:2d} ({n:3d} docs)  skip — below MIN_DOCS={MIN_DOCS}")
        continue

    docs = sub_df["text"].fillna("").tolist()
    k    = auto_k(n)

    tfidf = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=3000,
        min_df=2,
        max_df=0.5,
        stop_words=STOP_WORDS,
    )
    X     = tfidf.fit_transform(docs)
    vocab = tfidf.get_feature_names_out()

    nmf = NMF(n_components=k, random_state=42, max_iter=500)
    W   = nmf.fit_transform(X)

    sub_df["subtopic"]       = W.argmax(axis=1)
    sub_df["subtopic_score"] = W.max(axis=1)

    subtopics = []
    for sid in range(k):
        keywords = [vocab[i] for i in nmf.components_[sid].argsort()[:-TOP_WORDS - 1:-1]]
        mask     = sub_df["subtopic"] == sid
        chunk    = sub_df[mask].nlargest(N_REPR_DOCS, "subtopic_score")

        repr_docs = [
            {"id": row["id"], "text": row["text"][:400], "score": int(row["score"])}
            for _, row in chunk.iterrows()
        ]

        subtopics.append({
            "subtopic_id": sid,
            "keywords":    keywords,
            "doc_count":   int(mask.sum()),
            "repr_docs":   repr_docs,
        })

    save_cols = ["id", "post_id", SOURCE_COL, "score", "created_utc",
                 "text", "topic", "subtopic", "subtopic_score"]
    save_cols += [c for c in ["url", "author"] if c in sub_df.columns and c not in save_cols]
    sub_df[save_cols].to_csv(OUT_DIR / f"topic_{tid:02d}.csv", index=False)

    counts     = [st["doc_count"] for st in subtopics]
    imbalanced = (max(counts) / max(min(counts), 1)) > IMBALANCE_RATIO
    if imbalanced:
        small_ids = [st["subtopic_id"] for st in subtopics if st["doc_count"] == min(counts)]
        for st in subtopics:
            st["imbalance_warning"] = st["subtopic_id"] in small_ids

    overview.append({
        "topic_id":         int(tid),
        "topic_name":       topic_name,
        "doc_count":        n,
        "n_subtopics":      k,
        "imbalanced_split": imbalanced,
        "subtopics":        subtopics,
    })

    flag       = " ⚠ imbalanced" if imbalanced else ""
    kw_preview = " | ".join(", ".join(st["keywords"][:3]) for st in subtopics)
    print(f"Topic {tid:2d} ({n:4d} docs) → {k} sub-topics{flag}: {kw_preview}")

with open(OUT_DIR / "overview.json", "w", encoding="utf-8") as f:
    json.dump(overview, f, indent=2, ensure_ascii=False)

print(f"\nDone. {len(overview)} topics → {OUT_DIR}/")
