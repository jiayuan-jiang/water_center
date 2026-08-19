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

Usage (Mastodon):
    python build_docs_data.py --platform mastodon \
        --corpus data/corpus_mastodon.jsonl \
        --topics-dir data/topics_mastodon \
        --out-dir frontend/public/data/mastodon
"""

import argparse
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--platform",   default="reddit", choices=["reddit", "bluesky", "mastodon"])
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

# ── Mastodon topic labels (valid signal only; noise topics omitted) ───────────
MASTODON_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion",
    1:  "Flooding & Flood Warnings",
    2:  "Great Lakes Restoration & Policy",
    4:  "Lake Rescues & Boating Incidents",
    5:  "Ice Cover & Winter Weather",
    6:  "Beach Safety & Swim Advisories",
    8:  "Environmental Policy & Regulation",
    10: "PFAS & Chemical Contamination",
    11: "Invasive Species & Wildlife",
    12: "Wildfire Smoke & Air Quality",
    14: "Fishing & Fish Populations",
    15: "Algal Blooms",
    17: "Data Centers & Water Consumption",
    21: "Line 5 Pipeline & Litigation",
    22: "Muskegon Waterfront Development",
    24: "Grand River & Riverfront Projects",
}

TOPIC_LABELS = {
    "reddit":   REDDIT_TOPIC_LABELS,
    "bluesky":  BLUESKY_TOPIC_LABELS,
    "mastodon": MASTODON_TOPIC_LABELS,
}[args.platform]

# ── Load data ─────────────────────────────────────────────────────────────────
topic_info = pd.read_csv(TOPIC_CSV)
docs_df    = pd.read_csv(DOCS_CSV)
corpus     = {json.loads(l)["id"]: json.loads(l)
              for l in CORPUS.open()}

# LLM-judged controversy score per topic — see spec/controversy-score.md
CONTROVERSY_CKPT = Path(f"data/analysis/.controversy_llm_checkpoint_{args.platform}.json")
controversy_by_topic = {}
if CONTROVERSY_CKPT.exists():
    for tid_str, gen in json.loads(CONTROVERSY_CKPT.read_text()).items():
        if "error" in gen:
            continue
        controversy_by_topic[int(tid_str)] = {
            "score":     gen.get("controversy_score"),
            "verdict":   gen.get("verdict"),
            "reasoning": gen.get("reasoning"),
            "quotes":    gen.get("supporting_quotes", []),
        }

# Emotion breakdown per topic — see emotion_llm.py (LLM-based, replaces the
# j-hartmann distilroberta classifier in sentiment_analysis.py)
SENTIMENT_CSV = Path(f"data/analysis/emotion_llm_by_topic_{args.platform}.csv")
emotion_by_topic = {}
EMOTION_KEYS = ["neutral", "fear", "joy", "surprise", "sadness", "anger", "disgust"]
if SENTIMENT_CSV.exists():
    for _, r in pd.read_csv(SENTIMENT_CSV).iterrows():
        emotion_by_topic[int(r["topic"])] = {
            "dominant": r["dominant_emotion"],
            "pct": {k: (0.0 if pd.isna(r.get(f"pct_emotion_{k}")) else float(r[f"pct_emotion_{k}"]))
                    for k in EMOTION_KEYS},
        }

# Per-comment sentiment + emotion — see sentiment_llm.py / emotion_llm.py
# (LLM-based, replace the cardiffnlp/j-hartmann RoBERTa classifiers in
# sentiment_analysis.py after manual review found they miss sarcasm/irony)
SENTIMENT_DOCS_CSV = Path(f"data/analysis/sentiment_llm_docs_{args.platform}.csv")
EMOTION_DOCS_CSV = Path(f"data/analysis/emotion_llm_docs_{args.platform}.csv")
emotion_by_doc = {}
if SENTIMENT_DOCS_CSV.exists():
    for r in pd.read_csv(SENTIMENT_DOCS_CSV).itertuples():
        emotion_by_doc.setdefault(str(r.id), {})["sentiment"] = r.sentiment
if EMOTION_DOCS_CSV.exists():
    for r in pd.read_csv(EMOTION_DOCS_CSV).itertuples():
        emotion_by_doc.setdefault(str(r.id), {})["emotion"] = r.emotion

# STEEP tags per topic — see steep_tag.py, spec/reddit-further-analysis.md#analysis-7
STEEP_CSV = Path("data/analysis/topic_steep.csv")
steep_by_topic = {}
if STEEP_CSV.exists():
    for r in pd.read_csv(STEEP_CSV).itertuples():
        if r.platform != args.platform:
            continue
        steep_by_topic[int(r.topic_id)] = {
            "tags": [t for t in str(r.steep_tags).split("; ") if t and t != "nan"],
            "rationale": r.rationale,
            "human_confirmed": not pd.isna(r.human_confirmed) and str(r.human_confirmed).strip() != "",
        }

# for Bluesky/Mastodon: only keep labeled (valid signal) topics
if args.platform in ("bluesky", "mastodon"):
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
        "id":          tid,
        "label":       TOPIC_LABELS.get(tid, f"Topic {tid}"),
        "keywords":    keywords,
        "count":       int(row["Count"]),
        "controversy": controversy_by_topic.get(tid),
        "emotion":     emotion_by_topic.get(tid),
        "steep":       steep_by_topic.get(tid),
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

        if args.platform == "mastodon":
            source  = str(row.get("author", raw.get("author", "")))
            url     = str(raw.get("url", ""))
        elif args.platform == "bluesky":
            author  = str(row.get("author", raw.get("author", "")))
            url     = f"https://bsky.app/profile/{author}/post/{cid}" if author and cid else ""
            source  = "bluesky"
        else:
            sub     = str(row.get("subreddit", ""))
            post_id = str(row.get("post_id") or raw.get("_post_id", ""))
            url     = f"https://www.reddit.com/r/{sub}/comments/{post_id}/_/{cid}/" if post_id and cid else ""
            source  = sub

        doc_emo = emotion_by_doc.get(cid, {})
        comments.append({
            "id":        cid,
            "source":    source,
            "score":     int(row.get("score", 0)),
            "date":      datetime.fromtimestamp(
                             float(row["created_utc"])
                         ).strftime("%Y-%m-%d") if pd.notna(row.get("created_utc")) else "",
            "text":      str(row.get("text", "")),
            "url":       url,
            "sentiment": doc_emo.get("sentiment"),
            "emotion":   doc_emo.get("emotion"),
        })

    out = {"topic_id": tid, "label": entry["label"],
           "keywords": entry["keywords"], "controversy": entry["controversy"],
           "emotion": entry["emotion"], "steep": entry["steep"], "comments": comments}
    path = TOPICS_DIR / f"t{tid}.json"
    path.write_text(json.dumps(out, ensure_ascii=False))
    kb = path.stat().st_size / 1024
    print(f"  t{tid}.json — {len(comments)} comments — {kb:.1f} KB")

print("\nDone.")
