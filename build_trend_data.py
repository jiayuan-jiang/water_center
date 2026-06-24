"""
Compute monthly trend data for all Reddit BERTopic topics and write to docs/data/.

Output: docs/data/reddit_topic_trends.json

Run from repo root:
    python build_trend_data.py
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from statsmodels.nonparametric.smoothers_lowess import lowess

DOCS_CSV  = Path("data/topics/documents_with_topics.csv")
OUT_PATH  = Path("docs/data/reddit_topic_trends.json")
LOESS_FRAC = 0.35

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


def r(v, decimals=4):
    """Round float or list of floats for compact JSON."""
    if isinstance(v, (list, np.ndarray)):
        return [round(float(x), decimals) for x in v]
    return round(float(v), decimals)


def main():
    df = pd.read_csv(DOCS_CSV, parse_dates=["created_dt"])
    df["month"] = df["created_dt"].dt.to_period("M")

    # full month index spanning the whole corpus
    all_months = pd.period_range(df["month"].min(), df["month"].max(), freq="M")
    month_strs = [str(m) for m in all_months]

    # monthly total (outlier -1 excluded)
    total_per_month = (
        df[df["topic"] >= 0]
        .groupby("month").size()
        .reindex(all_months, fill_value=0)
    )

    topics_out = []
    for tid, label in sorted(TOPIC_LABELS.items()):
        topic_docs = df[df["topic"] == tid]
        count_per_month = (
            topic_docs.groupby("month").size()
            .reindex(all_months, fill_value=0)
        )

        counts  = count_per_month.values.astype(int)
        totals  = total_per_month.values.astype(int)
        share   = np.where(totals > 0, counts / totals, 0.0)

        x_num   = np.arange(len(all_months))
        smoothed = lowess(share, x_num, frac=LOESS_FRAC, return_sorted=False)
        smoothed = np.clip(smoothed, 0, None)

        active = int((counts > 0).sum())

        topics_out.append({
            "topic_id":     tid,
            "label":        label,
            "total_docs":   int(counts.sum()),
            "active_months": active,
            "monthly": {
                "count":  counts.tolist(),
                "total":  totals.tolist(),
                "share":  r(share),
                "loess":  r(smoothed),
            },
        })

    payload = {
        "meta": {
            "source":       "Reddit via Arctic Shift API",
            "platform":     "reddit",
            "corpus_file":  "data/topics/documents_with_topics.csv",
            "date_range":   {"start": month_strs[0], "end": month_strs[-1]},
            "total_corpus_docs": int(df[df["topic"] >= 0]["topic"].count()),
            "outlier_docs_excluded": int((df["topic"] == -1).sum()),
            "loess_frac":   LOESS_FRAC,
            "normalization": "share = topic_docs_per_month / total_non_outlier_corpus_docs_per_month",
            "generated":    datetime.now().isoformat()[:10],
        },
        "months":  month_strs,
        "topics":  topics_out,
    }

    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Written: {OUT_PATH}  ({size_kb:.1f} KB, {len(topics_out)} topics, {len(month_strs)} months)")


if __name__ == "__main__":
    main()
