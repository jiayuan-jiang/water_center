"""
Grounded emerging-issue candidate list from outlier micro-clusters.
Spec: spec/outlier-emerging-issues.md (Stage 3)

Input:  data/analysis/outlier_overview_{platform}.json  (from outlier_analysis.py)
Output: data/analysis/emerging_issues_candidates_{platform}.md
        data/analysis/.candidates_checkpoint_{platform}.json  (read by build_outlier_data.py)

Reads OPENAI_API_KEY from environment or .env.

Usage:
    python outlier_candidates.py --platform all
    python outlier_candidates.py --platform bluesky --dry-run
"""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from grounded_summary import strip_fences, load_checkpoint, save_checkpoint

SYSTEM_PROMPT = """You are analyzing social media discussion about the Great Lakes for a university Horizon Scan project that surfaces emerging ecological and socioeconomic issues.

You will receive a small cluster of posts/comments that did NOT fit any major discussion topic — it may contain an early weak signal. You get the cluster's keywords and up to 3 representative documents, each with an ID.

An emerging issue: receives little or no attention, is poorly understood, has no clear solutions or governance yet, could impact the Great Lakes basin within 10-20 years, or exists now but may grow greatly in magnitude. It must relate to water in some way.

Your task: output a single JSON object describing this cluster as a candidate emerging issue, based ONLY on the provided documents.

Output schema (raw JSON only — no markdown, no explanation):
{
  "issue": "Short issue title (4-8 words), phrased as an issue, not a topic label",
  "description": "2-3 sentences: what people are discussing and why it could be an emerging issue for the Great Lakes. Cite document IDs inline as [id] for every claim.",
  "water_related": true or false — whether the cluster genuinely relates to Great Lakes water issues,
  "key_quotes": [
    {"id": "<document id>", "quote": "<exact short phrase from the text, under 20 words>"}
  ]
}

Rules:
- Never invent facts not present in the provided documents
- If the cluster is clearly off-topic chatter (sports, memes, generic politics), set water_related to false and still fill the other fields honestly
- key_quotes must use exact text from the documents (verbatim substring), 1-3 quotes
- Output ONLY valid JSON, nothing else"""


def build_user_prompt(cluster: dict) -> str:
    lines = [
        f"Cluster keywords: {', '.join(cluster['keywords'])}",
        f"Document count: {cluster['n_docs']}",
        f"Active from {cluster['first_month']} to {cluster['last_month']}, "
        f"{cluster['recency']:.0%} of docs in the last 12 months",
        "",
        "Representative documents:",
    ]
    for doc in cluster["repr_docs"]:
        lines.append(f"\n[{doc['id']}] (engagement score={doc['score']})")
        lines.append(doc["text"])
    return "\n".join(lines)


def process_platform(platform: str, client, model_name: str, dry_run: bool):
    overview_path = Path(f"data/analysis/outlier_overview_{platform}.json")
    ckpt_path = Path(f"data/analysis/.candidates_checkpoint_{platform}.json")
    out_path = Path(f"data/analysis/emerging_issues_candidates_{platform}.md")

    data = json.loads(overview_path.read_text())
    clusters = data["clusters"]
    checkpoint = load_checkpoint(ckpt_path)
    print(f"[{platform}] {len(checkpoint)}/{len(clusters)} clusters already done")

    for cluster in clusters:
        key = str(cluster["cluster_id"])
        if key in checkpoint:
            continue
        if dry_run:
            checkpoint[key] = {"issue": "DRY RUN", "description": "dry run",
                               "water_related": True, "key_quotes": []}
            continue
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": build_user_prompt(cluster)},
                    ],
                    response_format={"type": "json_object"},
                )
                text = strip_fences(resp.choices[0].message.content)
                checkpoint[key] = json.loads(text)
                save_checkpoint(ckpt_path, checkpoint)
                print(f"  [{key}] {checkpoint[key].get('issue', '?')}")
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
                    raise

    source = {"reddit": "Reddit", "bluesky": "Bluesky", "mastodon": "Mastodon"}[platform]
    lines = [
        f"# Emerging Issue Candidates — {source} outlier analysis",
        "",
        f"Generated from {data['n_passing']} relevance-passing micro-clusters "
        f"({data['n_outlier_docs']:,} outlier docs re-clustered; "
        f"params: {json.dumps(data['params'])}).",
        "Ranked by novelty × recency. `water_related=false` rows are the LLM's "
        "off-topic verdicts — kept for transparency, review-and-discard.",
        "",
        "| # | Issue | Description | Source | Docs | Active | Novelty | Recency | Water? |",
        "|---|-------|-------------|--------|------|--------|---------|---------|--------|",
    ]
    for i, cluster in enumerate(clusters, 1):
        gen = checkpoint.get(str(cluster["cluster_id"]), {})
        if "error" in gen:
            continue
        desc = gen.get("description", "").replace("|", "\\|").replace("\n", " ")
        quotes = " ".join(f"«{q['quote']}»" for q in gen.get("key_quotes", [])[:2])
        quotes = quotes.replace("|", "\\|")
        lines.append(
            f"| {i} | {gen.get('issue', '?')} | {desc} {quotes} | {source} "
            f"| {cluster['n_docs']} | {cluster['first_month']}→{cluster['last_month']} "
            f"| {cluster['novelty']:.2f} | {cluster['recency']:.0%} "
            f"| {'✓' if gen.get('water_related') else '✗'} |"
        )
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Written → {out_path}  ({len(clusters)} candidates)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"],
                        default="reddit")
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
