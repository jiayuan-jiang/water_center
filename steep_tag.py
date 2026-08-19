"""
STEEP tag generation for Reddit/Bluesky topics and outlier micro-clusters.
Spec: spec/reddit-further-analysis.md#analysis-7-steep-categorization

Framework: Social / Technological / Economic / Environmental / Political
(Legal folded into Political per spec definition; no separate Values axis.)

Input:
    data/topics/topic_summary.csv                          (Reddit's 34 topics)
    data/topics_bluesky/topic_summary.csv                  (Bluesky's 28 labeled topics)
    data/analysis/outlier_overview_{platform}.json         (cluster keywords + metadata)
    data/analysis/.candidates_checkpoint_{platform}.json   (grounded issue/description)

Output:
    data/analysis/topic_steep.csv     (Reddit 34 + Bluesky 28 topics)
    data/analysis/outlier_steep.csv   (Reddit 66 + Bluesky 431 clusters)

Each row gets an LLM-suggested 1-2 STEEP tags + one-line rationale, plus an
empty `human_confirmed` column left for manual review.

Reads OPENAI_API_KEY from environment or .env.

Usage:
    python steep_tag.py --target topics --platform all
    python steep_tag.py --target outliers --platform all
    python steep_tag.py --target all --dry-run
"""

import argparse
import ast
import csv
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from grounded_summary import strip_fences, load_checkpoint, save_checkpoint

STEEP_CATEGORIES = ["Social", "Technological", "Economic", "Environmental", "Political"]

SYSTEM_PROMPT = """You are classifying items from a Great Lakes social-media Horizon Scan project using the STEEP framework:

- Social: public attitudes, community behavior, demographics
- Technological: new technologies, innovation, data systems
- Economic: jobs, industry, markets, costs
- Environmental: ecosystems, climate, species, water quality
- Political: policy, regulation, governance, legal

You will receive a topic or issue with its keywords/description. Output a single JSON object:
{
  "tags": ["<1 or 2 categories from Social, Technological, Economic, Environmental, Political>"],
  "rationale": "<one sentence: why these tags, not the others that also touch this item>"
}

Rules:
- Pick 1-2 tags maximum. Choose the categories that best explain the CORE driving force, not every dimension the item touches.
- Use only the five category names, exact spelling, from the list above.
- Output ONLY valid JSON, nothing else."""


def call_llm(client, model_name: str, user_prompt: str) -> dict:
    resp = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(strip_fences(resp.choices[0].message.content))


def tag_items(items: dict, ckpt_path: Path, client, model_name: str, dry_run: bool):
    """items: {key: user_prompt}. Mutates/saves a checkpoint dict of {key: {"tags": [...], "rationale": ...}}"""
    checkpoint = load_checkpoint(ckpt_path)
    print(f"  {len(checkpoint)}/{len(items)} already done ({ckpt_path.name})")

    for key, prompt in items.items():
        if key in checkpoint:
            continue
        if dry_run:
            checkpoint[key] = {"tags": ["Environmental"], "rationale": "dry run"}
            continue
        for attempt in range(3):
            try:
                result = call_llm(client, model_name, prompt)
                tags = [t for t in result.get("tags", []) if t in STEEP_CATEGORIES][:2]
                checkpoint[key] = {"tags": tags, "rationale": result.get("rationale", "")}
                save_checkpoint(ckpt_path, checkpoint)
                print(f"    [{key}] {tags}")
                time.sleep(0.3)
                break
            except json.JSONDecodeError as e:
                print(f"    [{key}] JSON parse error (attempt {attempt+1}): {e}")
                if attempt == 2:
                    checkpoint[key] = {"tags": [], "rationale": f"error: {e}"}
                    save_checkpoint(ckpt_path, checkpoint)
            except Exception as e:
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    wait = 60 * (attempt + 1)
                    print(f"    [{key}] Rate limited — waiting {wait}s")
                    time.sleep(wait)
                else:
                    raise
    return checkpoint


# ── Topic labels (mirrors build_docs_data.py REDDIT_TOPIC_LABELS / BLUESKY_TOPIC_LABELS) ──
REDDIT_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion", 1:  "Great Lakes Regional Overview",
    2:  "Invasive Species", 3:  "Waterfront & Tourism", 4:  "Swimming & Recreation",
    5:  "Beaches & Shorelines", 6:  "Water Temperature",
    7:  "Climate Change & Seasonal Shifts", 8:  "Ice Cover & Ice Fishing",
    9:  "PFAS & Chemical Contamination", 10: "Data Centers & Water Consumption",
    11: "Sport Fishing", 12: "Fisheries Management",
    13: "EPA & Environmental Regulation", 14: "Drinking Water Safety",
    15: "Offshore Wind Energy", 16: "Mining & Industrial Pollution",
    17: "Lake Water Levels", 18: "Midwest Climate Patterns",
    19: "Environmental Advocacy", 20: "Wildlife & Conservation",
    21: "Lake Erie Ecology", 22: "Lake Superior — North Shore",
    23: "Lake Huron Debris & Incidents", 24: "Kayaking & Boating",
    25: "Insects & Camping", 26: "Lake Ontario — Toronto Area",
    27: "Water Safety & Accidents", 28: "Scenic Views & Aesthetics",
    29: "Algal Blooms", 30: "Lake Michigan Overview", 31: "Lakeside Living",
    32: "Water Privatization (Nestlé)", 33: "Recreational Boating",
}

BLUESKY_TOPIC_LABELS = {
    0:  "General Great Lakes Discussion", 1:  "Wildlife & Conservation",
    4:  "Fisheries & Invasive Species", 5:  "Severe Weather & Navigation Safety",
    10: "Oil Pipeline & Energy Infrastructure", 13: "Geology & Shoreline Fossils",
    15: "Offshore Wind Energy", 18: "Data Centers & AI Water Consumption",
    19: "Great Lakes Borders & Governance", 26: "Algal Blooms & Invasive Plants",
    27: "Squall & Storm Warnings", 28: "EPA & Environmental Regulation",
    29: "Indigenous Communities & Water Rights", 31: "Dunes & Shoreline Parks",
    32: "NOAA & Scientific Research Funding", 33: "Sea Lamprey & Parasitic Species",
    35: "UFO/UAP Sightings Over Great Lakes", 36: "Great Lakes Shipping & Trade",
    39: "Cloud Cover & Weather Patterns", 41: "Lake-Effect Weather",
    43: "Mining & Nuclear Waste", 45: "PFAS & Chemical Contamination",
    46: "Microplastics", 48: "Marine Weather Warnings", 49: "Ice Cover Tracking",
    50: "Wildfire Smoke & Air Quality", 53: "Climate Change & Seasonal Shifts",
    59: "Coast Guard & Maritime Safety",
}

MASTODON_TOPIC_LABELS = {
    0: "General Great Lakes Discussion", 1: "Flooding & Flood Warnings",
    2: "Great Lakes Restoration & Policy", 4: "Lake Rescues & Boating Incidents",
    5: "Ice Cover & Winter Weather", 6: "Beach Safety & Swim Advisories",
    8: "Environmental Policy & Regulation", 10: "PFAS & Chemical Contamination",
    11: "Invasive Species & Wildlife", 12: "Wildfire Smoke & Air Quality",
    14: "Fishing & Fish Populations", 15: "Algal Blooms",
    17: "Data Centers & Water Consumption", 21: "Line 5 Pipeline & Litigation",
    22: "Muskegon Waterfront Development", 24: "Grand River & Riverfront Projects",
}

TOPIC_LABELS_BY_PLATFORM = {
    "reddit": REDDIT_TOPIC_LABELS, "bluesky": BLUESKY_TOPIC_LABELS,
    "mastodon": MASTODON_TOPIC_LABELS,
}
TOPIC_DIR_BY_PLATFORM = {
    "reddit": "data/topics", "bluesky": "data/topics_bluesky",
    "mastodon": "data/topics_mastodon",
}


def collect_topic_rows(platform: str, client, model_name: str, dry_run: bool) -> list:
    print(f"=== topics ({platform}) ===")
    labels = TOPIC_LABELS_BY_PLATFORM[platform]
    df_path = Path(TOPIC_DIR_BY_PLATFORM[platform]) / "topic_summary.csv"
    rows = []
    with df_path.open() as f:
        for row in csv.DictReader(f):
            tid = int(row["Topic"])
            if tid not in labels:
                continue
            keywords = ast.literal_eval(row["Representation"])[:10]
            rows.append({"topic_id": tid, "label": labels[tid], "keywords": keywords})
    rows.sort(key=lambda r: r["topic_id"])

    items = {
        str(r["topic_id"]): f"Topic label: {r['label']}\nKeywords: {', '.join(r['keywords'])}"
        for r in rows
    }
    ckpt_path = Path(f"data/analysis/.steep_checkpoint_topics_{platform}.json")
    checkpoint = tag_items(items, ckpt_path, client, model_name, dry_run)

    out_rows = []
    for r in rows:
        gen = checkpoint.get(str(r["topic_id"]), {})
        out_rows.append([platform, r["topic_id"], r["label"], "; ".join(r["keywords"]),
                          "; ".join(gen.get("tags", [])), gen.get("rationale", ""), ""])
    return out_rows


def write_topic_csv(new_rows_by_platform: dict):
    """Merge freshly-tagged platforms into topic_steep.csv without clobbering
    rows for platforms not processed in this run."""
    out_path = Path("data/analysis/topic_steep.csv")
    header = ["platform", "topic_id", "label", "keywords", "steep_tags", "rationale", "human_confirmed"]
    existing_rows = []
    if out_path.exists():
        with out_path.open(newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)
            if first_row == header:
                existing_rows = [row for row in reader if row[0] not in new_rows_by_platform]
            # else: old pre-platform-column schema — discard, will be fully regenerated

    all_rows = existing_rows
    for platform, rows in new_rows_by_platform.items():
        all_rows += rows
    all_rows.sort(key=lambda r: (r[0], int(r[1])))

    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(all_rows)
    print(f"Written -> {out_path} ({len(all_rows)} total topics)")


def collect_outlier_rows(platform: str, client, model_name: str, dry_run: bool) -> list:
    print(f"=== outliers ({platform}) ===")
    overview = json.loads(Path(f"data/analysis/outlier_overview_{platform}.json").read_text())
    candidates = load_checkpoint(Path(f"data/analysis/.candidates_checkpoint_{platform}.json"))

    rows = []
    for cluster in overview["clusters"]:
        cid = cluster["cluster_id"]
        gen = candidates.get(str(cid), {})
        if "error" in gen:
            continue
        rows.append({
            "cluster_id": cid,
            "issue": gen.get("issue", ""),
            "description": gen.get("description", ""),
            "keywords": cluster["keywords"][:10],
        })

    items = {
        str(r["cluster_id"]): (
            f"Issue: {r['issue']}\nDescription: {r['description']}\n"
            f"Keywords: {', '.join(r['keywords'])}"
        )
        for r in rows
    }
    ckpt_path = Path(f"data/analysis/.steep_checkpoint_outliers_{platform}.json")
    checkpoint = tag_items(items, ckpt_path, client, model_name, dry_run)

    out_rows = []
    for r in rows:
        gen = checkpoint.get(str(r["cluster_id"]), {})
        out_rows.append([platform, r["cluster_id"], r["issue"],
                          "; ".join(gen.get("tags", [])), gen.get("rationale", ""), ""])
    return out_rows


def write_outlier_csv(new_rows_by_platform: dict):
    """Merge freshly-tagged platforms into outlier_steep.csv without clobbering
    rows for platforms not processed in this run."""
    out_path = Path("data/analysis/outlier_steep.csv")
    header = ["platform", "cluster_id", "issue", "steep_tags", "rationale", "human_confirmed"]
    existing_rows = []
    if out_path.exists():
        with out_path.open(newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            existing_rows = [row for row in reader if row[0] not in new_rows_by_platform]

    all_rows = existing_rows
    for platform, rows in new_rows_by_platform.items():
        all_rows += rows

    with out_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(all_rows)
    print(f"Written -> {out_path} ({len(all_rows)} total clusters)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["topics", "outliers", "all"], default="all")
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"], default="all")
    parser.add_argument("--provider", choices=["openai", "deepseek"], default="openai")
    parser.add_argument("--model", default=None, help="default: gpt-4o-mini (openai) / deepseek-chat (deepseek)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.model is None:
        args.model = "deepseek-chat" if args.provider == "deepseek" else "gpt-4o-mini"

    if not args.dry_run:
        load_dotenv()
        if args.provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                raise SystemExit("DEEPSEEK_KEY is not set (env or .env)")
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise SystemExit("OPENAI_API_KEY is not set (env or .env)")
            client = OpenAI(api_key=api_key)
    else:
        client = None

    if args.target in ("topics", "all"):
        platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
        new_rows_by_platform = {
            p: collect_topic_rows(p, client, args.model, args.dry_run) for p in platforms
        }
        write_topic_csv(new_rows_by_platform)

    if args.target in ("outliers", "all"):
        platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
        new_rows_by_platform = {
            p: collect_outlier_rows(p, client, args.model, args.dry_run) for p in platforms
        }
        write_outlier_csv(new_rows_by_platform)


if __name__ == "__main__":
    main()