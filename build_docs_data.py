"""
Generate JSON data files for GitHub Pages topic browser.
Output: docs/data/topics.json + docs/data/topics/t{id}.json
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

CORPUS      = Path("data/corpus.jsonl")
TOPIC_CSV   = Path("data/topics/topic_summary.csv")
DOCS_CSV    = Path("data/topics/documents_with_topics.csv")
OUT_DIR     = Path("docs/data")
TOPICS_DIR  = OUT_DIR / "topics"
TOPICS_DIR.mkdir(parents=True, exist_ok=True)

MAX_COMMENTS_PER_TOPIC = 60  # cap to keep file sizes small

TOPIC_LABELS = {
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

# ── Load data ─────────────────────────────────────────────────────────────────
topic_info = pd.read_csv(TOPIC_CSV)
docs_df    = pd.read_csv(DOCS_CSV)
corpus     = {json.loads(l)["id"]: json.loads(l)
              for l in CORPUS.open()}

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
        sub     = str(row.get("subreddit", ""))
        post_id = str(row.get("post_id") or raw.get("_post_id", ""))
        url     = f"https://www.reddit.com/r/{sub}/comments/{post_id}/_/{cid}/" if post_id and cid else ""

        comments.append({
            "id":        cid,
            "subreddit": sub,
            "score":     int(row.get("score", 0)),
            "date":      datetime.fromtimestamp(
                             float(row["created_utc"])
                         ).strftime("%Y-%m-%d") if pd.notna(row.get("created_utc")) else "",
            "text":      str(row.get("text", "")),
            "url":       url,
        })

    out = {"topic_id": tid, "label": entry["label"],
           "keywords": entry["keywords"], "comments": comments}
    path = TOPICS_DIR / f"t{tid}.json"
    path.write_text(json.dumps(out, ensure_ascii=False))
    kb = path.stat().st_size / 1024
    print(f"  t{tid}.json — {len(comments)} comments — {kb:.1f} KB")

print("\nDone.")
