"""
Generate JSON data files for GitHub Pages topic browser.
Output: docs/data/topics.json + docs/data/topics/t{id}.json

Usage (Reddit, default):
    python build_docs_data.py

Usage (Bluesky):
    python build_docs_data.py --platform bluesky \
        --corpus data/corpus_bluesky.jsonl \
        --topics-dir data/topics_bluesky \
        --out-dir docs/data/bluesky
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--platform",   default="reddit", choices=["reddit", "bluesky"])
parser.add_argument("--corpus",     default="data/corpus.jsonl")
parser.add_argument("--topics-dir", default="data/topics")
parser.add_argument("--out-dir",    default="docs/data")
args = parser.parse_args()

CORPUS      = Path(args.corpus)
TOPIC_CSV   = Path(args.topics_dir) / "topic_summary.csv"
DOCS_CSV    = Path(args.topics_dir) / "documents_with_topics.csv"
OUT_DIR     = Path(args.out_dir)
TOPICS_DIR  = OUT_DIR / "topics"
TOPICS_DIR.mkdir(parents=True, exist_ok=True)

MAX_COMMENTS_PER_TOPIC = 60  # cap to keep file sizes small

# ── Reddit topic labels ───────────────────────────────────────────────────────
REDDIT_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion",
    1:  "Great Lakes Regional Overview",
    2:  "Invasive Species",
    3:  "Waterfront & Tourism",
    4:  "Swimming & Recreation",
    5:  "Beaches & Shorelines",
    6:  "Water Temperature",
    7:  "Climate Change & Seasonal Shifts",
    8:  "Ice Cover & Ice Fishing",
    9:  "PFAS & Chemical Contamination",
    10: "Data Centers & Water Consumption",
    11: "Sport Fishing",
    12: "Fisheries Management",
    13: "EPA & Environmental Regulation",
    14: "Drinking Water Safety",
    15: "Offshore Wind Energy",
    16: "Mining & Industrial Pollution",
    17: "Lake Water Levels",
    18: "Midwest Climate Patterns",
    19: "Environmental Advocacy",
    20: "Wildlife & Conservation",
    21: "Lake Erie Ecology",
    22: "Lake Superior — North Shore",
    23: "Lake Huron Debris & Incidents",
    24: "Kayaking & Boating",
    25: "Insects & Camping",
    26: "Lake Ontario — Toronto Area",
    27: "Water Safety & Accidents",
    28: "Scenic Views & Aesthetics",
    29: "Algal Blooms",
    30: "Lake Michigan Overview",
    31: "Lakeside Living",
    32: "Water Privatization (Nestlé)",
    33: "Recreational Boating",
}

# ── Bluesky topic labels (valid signal only; noise topics omitted) ────────────
BLUESKY_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion",
    1:  "Wildlife & Conservation",
    4:  "Fisheries & Invasive Species",
    5:  "Severe Weather & Navigation Safety",
    10: "Oil Pipeline & Energy Infrastructure",
    13: "Geology & Shoreline Fossils",
    15: "Offshore Wind Energy",
    18: "Data Centers & AI Water Consumption",
    19: "Great Lakes Borders & Governance",
    26: "Algal Blooms & Invasive Plants",
    27: "Squall & Storm Warnings",
    28: "EPA & Environmental Regulation",
    29: "Indigenous Communities & Water Rights",
    31: "Dunes & Shoreline Parks",
    32: "NOAA & Scientific Research Funding",
    33: "Sea Lamprey & Parasitic Species",
    35: "UFO/UAP Sightings Over Great Lakes",
    36: "Great Lakes Shipping & Trade",
    39: "Cloud Cover & Weather Patterns",
    41: "Lake-Effect Weather",
    43: "Mining & Nuclear Waste",
    45: "PFAS & Chemical Contamination",
    46: "Microplastics",
    48: "Marine Weather Warnings",
    49: "Ice Cover Tracking",
    50: "Wildfire Smoke & Air Quality",
    53: "Climate Change & Seasonal Shifts",
    59: "Coast Guard & Maritime Safety",
}

TOPIC_LABELS = BLUESKY_TOPIC_LABELS if args.platform == "bluesky" else REDDIT_TOPIC_LABELS

# ── Load data ─────────────────────────────────────────────────────────────────
topic_info = pd.read_csv(TOPIC_CSV)
docs_df    = pd.read_csv(DOCS_CSV)
corpus     = {json.loads(l)["id"]: json.loads(l)
              for l in CORPUS.open()}

# for Bluesky: only keep labeled (valid signal) topics
if args.platform == "bluesky":
    topic_info = topic_info[topic_info["Topic"].isin(TOPIC_LABELS)].copy()
else:
    topic_info = topic_info[topic_info["Topic"] != -1].copy()

# ── topics.json — index file ──────────────────────────────────────────────────
topics_index = []
for _, row in topic_info.sort_values("Count", ascending=False).iterrows():
    tid = int(row["Topic"])
    # parse keywords from BERTopic name string
    raw_name = row["Name"]
    parts = raw_name.split("_")[1:]          # drop leading index
    keywords = [k.strip() for k in parts if k.strip()]

    topics_index.append({
        "id":       tid,
        "label":    TOPIC_LABELS.get(tid, f"Topic {tid}"),
        "keywords": keywords,
        "count":    int(row["Count"]),
    })

(OUT_DIR / "topics.json").write_text(
    json.dumps({"generated": datetime.now().isoformat()[:10],
                "topics": topics_index}, ensure_ascii=False, indent=2)
)
print(f"topics.json — {len(topics_index)} topics")

# ── per-topic comment files ───────────────────────────────────────────────────
for entry in topics_index:
    tid = entry["id"]
    subset = docs_df[docs_df["topic"] == tid].copy()

    # sort by score descending, take top N
    subset = subset.sort_values("score", ascending=False).head(MAX_COMMENTS_PER_TOPIC)

    comments = []
    for _, row in subset.iterrows():
        cid = str(row.get("id", ""))
        raw = corpus.get(cid, {})

        if args.platform == "bluesky":
            author  = str(row.get("author", raw.get("author", "")))
            url     = f"https://bsky.app/profile/{author}/post/{cid}" if author and cid else ""
            source  = "bluesky"
        else:
            sub     = str(row.get("subreddit", ""))
            post_id = str(row.get("post_id") or raw.get("_post_id", ""))
            url     = f"https://www.reddit.com/r/{sub}/comments/{post_id}/_/{cid}/" if post_id and cid else ""
            source  = sub

        comments.append({
            "id":     cid,
            "source": source,
            "score":  int(row.get("score", 0)),
            "date":   datetime.fromtimestamp(
                          float(row["created_utc"])
                      ).strftime("%Y-%m-%d") if pd.notna(row.get("created_utc")) else "",
            "text":   str(row.get("text", "")),
            "url":    url,
        })

    out = {"topic_id": tid, "label": entry["label"],
           "keywords": entry["keywords"], "comments": comments}
    path = TOPICS_DIR / f"t{tid}.json"
    path.write_text(json.dumps(out, ensure_ascii=False))
    kb = path.stat().st_size / 1024
    print(f"  t{tid}.json — {len(comments)} comments — {kb:.1f} KB")

print("\nDone.")
