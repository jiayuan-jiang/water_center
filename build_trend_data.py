"""
Compute monthly trend data for BERTopic topics and write to docs/data/.

Usage (Reddit, default):
    python build_trend_data.py

Usage (Bluesky):
    python build_trend_data.py --platform bluesky
"""

import argparse
import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from statsmodels.nonparametric.smoothers_lowess import lowess

LOESS_FRAC = 0.35

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
    35: "Environmental Advocacy",
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

PLATFORM_CONFIG = {
    "reddit": {
        "labels":      REDDIT_TOPIC_LABELS,
        "docs_csv":    "data/topics/documents_with_topics.csv",
        "out_path":    "docs/data/reddit_topic_trends.json",
        "source":      "Reddit via Arctic Shift API",
    },
    "bluesky": {
        "labels":      BLUESKY_TOPIC_LABELS,
        "docs_csv":    "data/topics_bluesky/documents_with_topics.csv",
        "out_path":    "docs/data/bluesky_topic_trends.json",
        "source":      "Bluesky via atproto searchPosts API",
    },
}


def r(v, decimals=4):
    if isinstance(v, (list, np.ndarray)):
        return [round(float(x), decimals) for x in v]
    return round(float(v), decimals)


def build(platform: str):
    cfg = PLATFORM_CONFIG[platform]
    docs_csv = Path(cfg["docs_csv"])
    out_path = Path(cfg["out_path"])
    topic_labels = cfg["labels"]

    df = pd.read_csv(docs_csv, parse_dates=["created_dt"])
    df["month"] = df["created_dt"].dt.to_period("M")

    all_months = pd.period_range(df["month"].min(), df["month"].max(), freq="M")
    month_strs = [str(m) for m in all_months]

    total_per_month = (
        df[df["topic"] >= 0]
        .groupby("month").size()
        .reindex(all_months, fill_value=0)
    )

    topics_out = []
    for tid, label in sorted(topic_labels.items()):
        count_per_month = (
            df[df["topic"] == tid].groupby("month").size()
            .reindex(all_months, fill_value=0)
        )

        counts   = count_per_month.values.astype(int)
        totals   = total_per_month.values.astype(int)
        share    = np.where(totals > 0, counts / totals, 0.0)
        x_num    = np.arange(len(all_months))
        smoothed = np.clip(lowess(share, x_num, frac=LOESS_FRAC, return_sorted=False), 0, None)

        topics_out.append({
            "topic_id":      tid,
            "label":         label,
            "total_docs":    int(counts.sum()),
            "active_months": int((counts > 0).sum()),
            "monthly": {
                "count": counts.tolist(),
                "total": totals.tolist(),
                "share": r(share),
                "loess": r(smoothed),
            },
        })

    payload = {
        "meta": {
            "source":               cfg["source"],
            "platform":             platform,
            "corpus_file":          cfg["docs_csv"],
            "date_range":           {"start": month_strs[0], "end": month_strs[-1]},
            "total_corpus_docs":    int(df[df["topic"] >= 0]["topic"].count()),
            "outlier_docs_excluded": int((df["topic"] == -1).sum()),
            "loess_frac":           LOESS_FRAC,
            "normalization":        "share = topic_docs_per_month / total_non_outlier_corpus_docs_per_month",
            "generated":            datetime.now().isoformat()[:10],
        },
        "months": month_strs,
        "topics": topics_out,
    }

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    size_kb = out_path.stat().st_size / 1024
    print(f"Written: {out_path}  ({size_kb:.1f} KB, {len(topics_out)} topics, {len(month_strs)} months)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "all"], default="reddit")
    args = parser.parse_args()

    platforms = ["reddit", "bluesky"] if args.platform == "all" else [args.platform]
    for p in platforms:
        build(p)


if __name__ == "__main__":
    main()
