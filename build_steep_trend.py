"""
Aggregate STEEP category monthly volume across topics + outlier clusters.
Spec: discussed with Manja/team 2026-07-30, extending spec/reddit-further-analysis.md#analysis-7

Combines two already-computed sources per platform:
  - Topic monthly counts:   frontend/public/data/{platform}_topic_trends.json
  - Outlier monthly counts: frontend/public/data/outliers/{platform}/clusters.json

...tagged with STEEP categories from:
  - data/analysis/topic_steep.csv
  - data/analysis/outlier_steep.csv

A topic/cluster with 2 tags contributes its full count to both categories, so
category shares can sum to >100% — this is intentional (STEEP tags are not
mutually exclusive) and shows relative weight, not a partition of the corpus.

Output: frontend/public/data/steep_trends/{platform}.json
    {
      "months": [...],
      "total_docs": [...],           # topics(non-outlier) + passing-outlier docs per month
      "categories": {
        "Environmental": {"count": [...], "share": [...]},
        ...
      }
    }

Usage:
    python build_steep_trend.py
    python build_steep_trend.py --platform bluesky
"""

import argparse
import csv
import json
from pathlib import Path

STEEP_CATEGORIES = ["Social", "Technological", "Economic", "Environmental", "Political"]


def load_topic_steep(platform: str) -> dict:
    tags = {}
    with open("data/analysis/topic_steep.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["platform"] != platform:
                continue
            tags[int(row["topic_id"])] = [t for t in row["steep_tags"].split("; ") if t]
    return tags


def load_outlier_steep(platform: str) -> dict:
    tags = {}
    with open("data/analysis/outlier_steep.csv", newline="") as f:
        for row in csv.DictReader(f):
            if row["platform"] != platform:
                continue
            tags[int(row["cluster_id"])] = [t for t in row["steep_tags"].split("; ") if t]
    return tags


def build_platform(platform: str):
    topic_trends = json.loads(Path(f"frontend/public/data/{platform}_topic_trends.json").read_text())
    outlier_clusters = json.loads(Path(f"frontend/public/data/outliers/{platform}/clusters.json").read_text())["clusters"]

    topic_tags = load_topic_steep(platform)
    outlier_tags = load_outlier_steep(platform)

    months = topic_trends["months"]
    month_idx = {m: i for i, m in enumerate(months)}
    n = len(months)

    category_count = {c: [0] * n for c in STEEP_CATEGORIES}
    total_docs = list(topic_trends["topics"][0]["monthly"]["total"]) if topic_trends["topics"] else [0] * n

    for t in topic_trends["topics"]:
        tags = topic_tags.get(t["topic_id"], [])
        counts = t["monthly"]["count"]
        for tag in tags:
            for i, v in enumerate(counts):
                category_count[tag][i] += v

    for c in outlier_clusters:
        tags = outlier_tags.get(c["id"], [])
        for month, v in c["monthly_counts"].items():
            i = month_idx.get(month)
            if i is None:
                continue
            total_docs[i] += v
            for tag in tags:
                category_count[tag][i] += v

    categories_out = {}
    for cat in STEEP_CATEGORIES:
        counts = category_count[cat]
        share = [(counts[i] / total_docs[i]) if total_docs[i] else 0.0 for i in range(n)]
        categories_out[cat] = {"count": counts, "share": [round(s, 4) for s in share]}

    out = {
        "platform": platform,
        "months": months,
        "total_docs": total_docs,
        "categories": categories_out,
    }
    out_dir = Path("frontend/public/data/steep_trends")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{platform}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False))
    print(f"[{platform}] {n} months -> {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "all"], default="all")
    args = parser.parse_args()
    platforms = ["reddit", "bluesky"] if args.platform == "all" else [args.platform]
    for p in platforms:
        build_platform(p)


if __name__ == "__main__":
    main()
