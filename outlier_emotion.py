"""
Emotion classification per outlier cluster (dominant emotion for the topic
browser's outlier list — see sentiment_analysis.py for the same model applied
to main topics).

Input:  data/analysis/outlier_docs_{platform}.csv (cluster, text, ...)
Output: data/analysis/outlier_emotion_{platform}.csv (per-cluster dominant_emotion + pct breakdown)
        data/analysis/outlier_doc_emotion_{platform}.csv (per-document emotion label)

Usage:
    python outlier_emotion.py --platform reddit
    python outlier_emotion.py --platform bluesky
"""

import argparse
import os
import pandas as pd
import torch
from pathlib import Path
from transformers import pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--platform", choices=["reddit", "bluesky"], default="reddit")
parser.add_argument("--batch-size", type=int, default=64)
args = parser.parse_args()

DOCS_FILE = Path(f"data/analysis/outlier_docs_{args.platform}.csv")
OUT_FILE = Path(f"data/analysis/outlier_emotion_{args.platform}.csv")
DOC_OUT_FILE = Path(f"data/analysis/outlier_doc_emotion_{args.platform}.csv")

EMOTION_MODEL = "j-hartmann/emotion-english-distilroberta-base"

if torch.cuda.is_available():
    DEVICE = 0
elif torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = -1
    torch.set_num_threads(os.cpu_count())


def run_pipeline(pipe, texts, batch_size):
    labels = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        for result in pipe(batch, batch_size=batch_size, truncation=True, max_length=512, top_k=1):
            top = result[0] if isinstance(result, list) else result
            labels.append(top["label"])
        if (i // batch_size) % 20 == 0:
            print(f"  {min(i + batch_size, len(texts)):,}/{len(texts):,}")
    return labels


def main():
    df = pd.read_csv(DOCS_FILE)
    df["text"] = df["text"].fillna("")
    print(f"Scoring {len(df):,} docs across {df['cluster'].nunique()} clusters ({args.platform})")

    emotion_pipe = pipeline("text-classification", model=EMOTION_MODEL, device=DEVICE)
    df["emotion"] = run_pipeline(emotion_pipe, df["text"].tolist(), args.batch_size)

    df[["id", "cluster", "emotion"]].to_csv(DOC_OUT_FILE, index=False)
    print(f"Written: {DOC_OUT_FILE} ({len(df):,} docs)")

    rows = []
    for cluster_id, group in df.groupby("cluster"):
        emo_pct = (group["emotion"].value_counts(normalize=True) * 100).to_dict()
        dominant_emotion = max(emo_pct, key=emo_pct.get)
        rows.append({
            "cluster": cluster_id,
            "n_docs": len(group),
            "dominant_emotion": dominant_emotion,
            **{f"pct_emotion_{k}": round(v, 1) for k, v in emo_pct.items()},
        })
    pd.DataFrame(rows).to_csv(OUT_FILE, index=False)
    print(f"Written: {OUT_FILE} ({len(rows):,} clusters)")


if __name__ == "__main__":
    main()
