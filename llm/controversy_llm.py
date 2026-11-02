"""
LLM-judged controversy score per topic.

Both cheaper proxies tried before this failed manual validation against 8
hand-read topics (see spec/controversy-score.md): sentiment-ratio
(Pearson -0.72 vs. manual read) and zero-shot NLI stance-ratio (-0.66) —
both false-positive on heterogeneous-but-uncontentious topics and
false-negative on lopsided-but-genuine debates. Manual reading of raw text
was the only thing that tracked real controversy, so this asks an LLM to do
that reading directly, per topic (not per document) — 62 calls total,
estimated ~$0.02 at gpt-4o-mini rates (see spec/controversy-score.md).

Samples each topic's highest-confidence negative- and positive-sentiment
comments (same sampling that surfaced clear examples during manual review)
and asks the model to judge genuine two-sided disagreement vs. one-sided
consensus vs. heterogeneous-but-uncontentious content.

Input:  data/analysis/sentiment_docs_{platform}.csv
        data/topics/documents_with_topics.csv | data/topics_bluesky/documents_with_topics.csv
Output: data/analysis/controversy_llm_{platform}.csv
        data/analysis/.controversy_llm_checkpoint_{platform}.json

Reads OPENAI_API_KEY from environment or .env.

Usage:
    python llm/controversy_llm.py --platform all
    python llm/controversy_llm.py --platform reddit --dry-run
"""

import argparse
import json
import os
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

from grounded_summary import strip_fences, load_checkpoint, save_checkpoint

REDDIT_TOPIC_LABELS = {
    0: "General Great Lakes Discussion", 1: "Great Lakes Regional Overview", 2: "Invasive Species",
    3: "Waterfront & Tourism", 4: "Swimming & Recreation", 5: "Beaches & Shorelines",
    6: "Water Temperature", 7: "Climate Change & Seasonal Shifts", 8: "Ice Cover & Ice Fishing",
    9: "PFAS & Chemical Contamination", 10: "Data Centers & Water Consumption", 11: "Sport Fishing",
    12: "Fisheries Management", 13: "EPA & Environmental Regulation", 14: "Drinking Water Safety",
    15: "Offshore Wind Energy", 16: "Mining & Industrial Pollution", 17: "Lake Water Levels",
    18: "Midwest Climate Patterns", 19: "Environmental Advocacy", 20: "Wildlife & Conservation",
    21: "Lake Erie Ecology", 22: "Lake Superior — North Shore", 23: "Lake Huron Debris & Incidents",
    24: "Kayaking & Boating", 25: "Insects & Camping", 26: "Lake Ontario — Toronto Area",
    27: "Water Safety & Accidents", 28: "Scenic Views & Aesthetics", 29: "Algal Blooms",
    30: "Lake Michigan Overview", 31: "Lakeside Living", 32: "Water Privatization (Nestlé)",
    33: "Recreational Boating",
}
BLUESKY_TOPIC_LABELS = {
    0: "General Great Lakes Discussion", 1: "Wildlife & Conservation", 4: "Fisheries & Invasive Species",
    5: "Severe Weather & Navigation Safety", 10: "Oil Pipeline & Energy Infrastructure",
    13: "Geology & Shoreline Fossils", 15: "Offshore Wind Energy", 18: "Data Centers & AI Water Consumption",
    19: "Great Lakes Borders & Governance", 26: "Algal Blooms & Invasive Plants", 27: "Squall & Storm Warnings",
    28: "EPA & Environmental Regulation", 29: "Indigenous Communities & Water Rights",
    31: "Dunes & Shoreline Parks", 32: "NOAA & Scientific Research Funding", 33: "Sea Lamprey & Parasitic Species",
    35: "UFO/UAP Sightings Over Great Lakes", 36: "Great Lakes Shipping & Trade",
    39: "Cloud Cover & Weather Patterns", 41: "Lake-Effect Weather", 43: "Mining & Nuclear Waste",
    45: "PFAS & Chemical Contamination", 46: "Microplastics", 48: "Marine Weather Warnings",
    49: "Ice Cover Tracking", 50: "Wildfire Smoke & Air Quality", 53: "Climate Change & Seasonal Shifts",
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

SYSTEM_PROMPT = """You are analyzing social media discourse about the Great Lakes for a university Horizon Scan project.

You will be given a discussion topic and a sample of comments about it (the most confidently positive- and negative-toned comments in the topic, per an automated sentiment classifier). Your job is to judge whether this topic reflects genuine controversy: real, substantively argued disagreement between people taking opposing positions.

This is NOT the same as "the comments have mixed positive/negative tone." Distinguish:
- genuine_debate: people are actively arguing opposing positions on the same specific question (e.g. arguing about who's at fault, whether a policy/technology is good or bad, disputing facts)
- one_sided_consensus: comments may be strongly emotional (very positive or very negative), but everyone actually agrees — no one is arguing the other side
- heterogeneous_not_contentious: comments differ in tone or cover different sub-topics/personal preferences, but nobody is arguing against anybody else's position — it's just varied content, not a debate

Output a single JSON object:
{
  "controversy_score": a number from 0 to 1 (0 = no real disagreement, 1 = an actively argued two-sided debate),
  "verdict": one of "genuine_debate", "one_sided_consensus", "heterogeneous_not_contentious",
  "reasoning": "1-2 sentences explaining the judgment, citing specific comment IDs as [id]",
  "supporting_quotes": [{"id": "<comment id>", "quote": "<short exact phrase from the text>"}]
}

Rules:
- Base your judgment only on the provided comments
- key quotes must use exact text from the documents (verbatim substring)
- Include 1-3 supporting_quotes
- Output ONLY valid JSON, nothing else"""


def build_user_prompt(label: str, sample: pd.DataFrame) -> str:
    lines = [f"Topic: {label}", f"Sample size: {len(sample)} comments", "", "Comments:"]
    for _, row in sample.iterrows():
        lines.append(f"\n[{row['id']}] (sentiment={row['sentiment']})")
        lines.append(str(row["text"])[:400])
    return "\n".join(lines)


def sample_docs(platform: str, topic_id: int, n_per_side: int = 8) -> pd.DataFrame:
    sent = pd.read_csv(f"data/analysis/sentiment_docs_{platform}.csv")
    docs_file = {
        "bluesky":  "data/topics_bluesky/documents_with_topics.csv",
        "mastodon": "data/topics_mastodon/documents_with_topics.csv",
    }.get(platform, "data/topics/documents_with_topics.csv")
    docs = pd.read_csv(docs_file)[["id", "text"]]
    merged = sent.merge(docs, on="id")
    sub = merged[merged["topic"] == topic_id]
    neg = sub[sub["sentiment"] == "negative"].sort_values("sentiment_score", ascending=False).head(n_per_side)
    pos = sub[sub["sentiment"] == "positive"].sort_values("sentiment_score", ascending=False).head(n_per_side)
    return pd.concat([neg, pos])


def process_platform(platform: str, client, model_name: str, dry_run: bool):
    labels = {
        "bluesky":  BLUESKY_TOPIC_LABELS,
        "mastodon": MASTODON_TOPIC_LABELS,
    }.get(platform, REDDIT_TOPIC_LABELS)
    ckpt_path = Path(f"data/analysis/.controversy_llm_checkpoint_{platform}.json")
    out_path = Path(f"data/analysis/controversy_llm_{platform}.csv")
    checkpoint = load_checkpoint(ckpt_path)
    print(f"[{platform}] {len(checkpoint)}/{len(labels)} topics already done")

    for topic_id, label in labels.items():
        key = str(topic_id)
        if key in checkpoint:
            continue

        sample = sample_docs(platform, topic_id)
        if len(sample) < 4:
            print(f"  SKIP [{key}] {label}: only {len(sample)} pos/neg docs (likely all-neutral bot spam)")
            checkpoint[key] = {"controversy_score": 0, "verdict": "insufficient_data",
                                "reasoning": f"Only {len(sample)} non-neutral comments available.",
                                "supporting_quotes": []}
            save_checkpoint(ckpt_path, checkpoint)
            continue
        if dry_run:
            print(f"  DRY [{key}] {label} (sample={len(sample)})")
            checkpoint[key] = {"controversy_score": 0, "verdict": "DRY RUN", "reasoning": "", "supporting_quotes": []}
            continue

        user_prompt = build_user_prompt(label, sample)
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
                text = strip_fences(resp.choices[0].message.content)
                result = json.loads(text)
                checkpoint[key] = result
                save_checkpoint(ckpt_path, checkpoint)
                print(f"  [{key}] {label}: {result.get('controversy_score')} ({result.get('verdict')})")
                time.sleep(0.3)
                break
            except json.JSONDecodeError as e:
                print(f"  [{key}] JSON parse error (attempt {attempt+1}): {e}")
                if attempt == 2:
                    checkpoint[key] = {"error": str(e), "raw": text[:500]}
                    save_checkpoint(ckpt_path, checkpoint)
            except Exception as e:
                if "quota" in str(e).lower() or "rate" in str(e).lower():
                    wait = 60 * (attempt + 1)
                    print(f"  [{key}] Rate limited — waiting {wait}s")
                    time.sleep(wait)
                else:
                    print(f"  [{key}] Error: {e}")
                    raise

    rows = []
    for topic_id, label in labels.items():
        gen = checkpoint.get(str(topic_id), {})
        if "error" in gen:
            continue
        quotes = " ".join(f"«{q['quote']}»" for q in gen.get("supporting_quotes", [])[:3])
        rows.append({
            "topic": topic_id, "label": label,
            "controversy_llm": gen.get("controversy_score"),
            "verdict": gen.get("verdict"),
            "reasoning": gen.get("reasoning"),
            "quotes": quotes,
        })
    out = pd.DataFrame(rows).sort_values("controversy_llm", ascending=False)
    out.to_csv(out_path, index=False)
    print(f"[{platform}] Written → {out_path} ({len(out)} topics)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"], default="reddit")
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

    platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
    for p in platforms:
        print(f"\n=== {p} ===")
        process_platform(p, client, args.model, args.dry_run)


if __name__ == "__main__":
    main()
