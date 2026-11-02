"""
Generate monthly trend chart for a single BERTopic topic.
Usage: python analysis/topic_trend_viz.py --topic 10 --label "Data Centers & Water Consumption"
"""

import argparse
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from statsmodels.nonparametric.smoothers_lowess import lowess

DOCS_PATH = "data/topics/documents_with_topics.csv"
OUT_DIR = "data/analysis"


def load_monthly(topic_id: int):
    df = pd.read_csv(DOCS_PATH, parse_dates=["created_dt"])
    df["month"] = df["created_dt"].dt.to_period("M")

    total_per_month = df[df["topic"] >= 0].groupby("month").size().rename("total")
    topic_per_month = (
        df[df["topic"] == topic_id].groupby("month").size().rename("count")
    )

    monthly = pd.DataFrame({"total": total_per_month, "count": topic_per_month}).fillna(0)
    monthly["share"] = monthly["count"] / monthly["total"]
    monthly.index = monthly.index.to_timestamp()
    return monthly


def plot_trend(monthly: pd.DataFrame, topic_id: int, label: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)

    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
    fig.suptitle(f"Topic {topic_id}: {label}\nMonthly Trend (Reddit, Jan 2023 – May 2026)", fontsize=13)

    months = monthly.index

    # — top panel: raw document count —
    ax1 = axes[0]
    ax1.bar(months, monthly["count"], width=20, color="#4C72B0", alpha=0.8)
    ax1.set_ylabel("Documents per month")
    ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax1.grid(axis="y", linestyle="--", alpha=0.4)

    # — bottom panel: share of monthly corpus —
    ax2 = axes[1]
    ax2.bar(months, monthly["share"] * 100, width=20, color="#DD8452", alpha=0.8)

    # LOESS smoothing (frac controls bandwidth: larger = smoother)
    x_num = np.arange(len(months))
    y_share = monthly["share"].values * 100
    smoothed = lowess(y_share, x_num, frac=0.35, return_sorted=False)
    smoothed = np.clip(smoothed, 0, None)  # share cannot be negative
    ax2.plot(months, smoothed, color="#c0392b", linewidth=2, label="LOESS smoothing (frac=0.35)")
    ax2.set_ylabel("Share of monthly corpus (%)")
    ax2.set_xlabel("Month")
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", linestyle="--", alpha=0.4)

    plt.tight_layout()
    out_path = os.path.join(out_dir, f"topic{topic_id}_trend.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"Saved: {out_path}")

    print(f"\n--- Topic {topic_id}: {label} ---")
    print(f"Total documents: {int(monthly['count'].sum())}")
    print(f"Active months (count > 0): {(monthly['count'] > 0).sum()} / {len(monthly)}")
    print(f"Peak month: {monthly['count'].idxmax().strftime('%Y-%m')} ({int(monthly['count'].max())} docs)")
    print(f"Share range: {monthly['share'].min()*100:.2f}% – {monthly['share'].max()*100:.2f}%")
    print(f"LOESS peak smoothed share: {smoothed.max():.2f}%")
    period_2023 = monthly.loc["2023":"2023", "share"].mean() * 100
    period_2024_26 = monthly.loc["2024":, "share"].mean() * 100
    print(f"Avg share 2023: {period_2023:.2f}%")
    print(f"Avg share 2024–2026: {period_2024_26:.2f}%")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", type=int, default=10)
    parser.add_argument("--label", type=str, default="Data Centers & Water Consumption")
    parser.add_argument("--out-dir", type=str, default=OUT_DIR)
    args = parser.parse_args()

    monthly = load_monthly(args.topic)
    plot_trend(monthly, args.topic, args.label, args.out_dir)


if __name__ == "__main__":
    main()
