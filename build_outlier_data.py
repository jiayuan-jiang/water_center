"""
Build frontend JSON for the outlier signal browser.
Spec: spec/outlier-emerging-issues.md

Input:  data/analysis/outlier_overview_{platform}.json
        data/analysis/outlier_docs_{platform}.csv
        data/analysis/.candidates_checkpoint_{platform}.json  (grounded, optional)
Output: frontend/public/data/outliers/{platform}/clusters.json
        frontend/public/data/outliers/{platform}/c{id}.json

Usage:
    python build_outlier_data.py                  # both platforms
    python build_outlier_data.py --platform reddit
"""

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

OUT_ROOT = Path("frontend/public/data/outliers")


def build_platform(platform: str):
    overview = json.loads(
        Path(f"data/analysis/outlier_overview_{platform}.json").read_text())
    docs = pd.read_csv(f"data/analysis/outlier_docs_{platform}.csv")
    ckpt_path = Path(f"data/analysis/.candidates_checkpoint_{platform}.json")
    grounded = json.loads(ckpt_path.read_text()) if ckpt_path.exists() else {}

    emotion_path = Path(f"data/analysis/outlier_emotion_{platform}.csv")
    emotion_by_cluster = {}
    EMOTION_KEYS = ["neutral", "fear", "joy", "surprise", "sadness", "anger", "disgust"]
    if emotion_path.exists():
        for _, r in pd.read_csv(emotion_path).iterrows():
            emotion_by_cluster[int(r["cluster"])] = {
                "dominant": r["dominant_emotion"],
                "pct": {k: (0.0 if pd.isna(r.get(f"pct_emotion_{k}")) else float(r[f"pct_emotion_{k}"]))
                        for k in EMOTION_KEYS},
            }

    doc_emotion_path = Path(f"data/analysis/outlier_doc_emotion_{platform}.csv")
    emotion_by_doc = {}
    if doc_emotion_path.exists():
        for _, r in pd.read_csv(doc_emotion_path).iterrows():
            emotion_by_doc[str(r["id"])] = r["emotion"]

    steep_path = Path("data/analysis/outlier_steep.csv")
    steep_by_cluster = {}
    if steep_path.exists():
        for _, r in pd.read_csv(steep_path).iterrows():
            if r["platform"] != platform:
                continue
            steep_by_cluster[int(r["cluster_id"])] = {
                "tags": [t for t in str(r["steep_tags"]).split("; ") if t and t != "nan"],
                "rationale": r["rationale"],
                "human_confirmed": not pd.isna(r["human_confirmed"]) and str(r["human_confirmed"]).strip() != "",
            }

    out_dir = OUT_ROOT / platform
    out_dir.mkdir(parents=True, exist_ok=True)

    source_col = "subreddit" if "subreddit" in docs.columns else "source"
    docs["date"] = pd.to_datetime(docs["created_dt"]).dt.strftime("%Y-%m-%d")

    clusters = []
    for c in overview["clusters"]:
        cid = c["cluster_id"]
        gen = grounded.get(str(cid), {})
        if "error" in gen:
            gen = {}
        clusters.append({
            "id": cid,
            "label": gen.get("issue") or " · ".join(c["keywords"][:3]),
            "grounded": bool(gen),
            "summary": gen.get("description"),
            "water_related": gen.get("water_related"),
            "key_quotes": gen.get("key_quotes", []),
            "keywords": c["keywords"],
            "n_docs": c["n_docs"],
            "relevance": c["relevance"],
            "novelty": c["novelty"],
            "recency": c["recency"],
            "rank_score": c["rank_score"],
            "first_month": c["first_month"],
            "last_month": c["last_month"],
            "monthly_counts": c["monthly_counts"],
            "emotion": emotion_by_cluster.get(cid),
            "steep": steep_by_cluster.get(cid),
        })

        sub = docs[docs["cluster"] == cid].sort_values("score", ascending=False)
        cluster_docs = [
            {"id": str(r["id"]), source_col: str(r[source_col]),
             "score": int(r["score"]), "date": r["date"], "text": str(r["text"]),
             "emotion": emotion_by_doc.get(str(r["id"]))}
            for _, r in sub.iterrows()
        ]
        (out_dir / f"c{cid}.json").write_text(json.dumps(
            {"cluster_id": cid, "docs": cluster_docs}, ensure_ascii=False))

    n_grounded = sum(1 for c in clusters if c["grounded"])
    index = {
        "generated": date.today().isoformat(),
        "platform": platform,
        "params": overview["params"],
        "n_outlier_docs": overview["n_outlier_docs"],
        "n_clusters_total": overview["n_clusters"],
        "n_passing": overview["n_passing"],
        "n_grounded": n_grounded,
        "clusters": clusters,
    }
    (out_dir / "clusters.json").write_text(
        json.dumps(index, ensure_ascii=False))
    print(f"[{platform}] {len(clusters)} clusters "
          f"({n_grounded} grounded), {len(docs)} docs → {out_dir}/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"],
                        default="all")
    args = parser.parse_args()
    platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
    for p in platforms:
        build_platform(p)


if __name__ == "__main__":
    main()
