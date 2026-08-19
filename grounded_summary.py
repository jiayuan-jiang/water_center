"""
grounded_summary.py — LLM-grounded summaries for each sub-topic.

For each subtopic in data/subtopics/overview.json (or bluesky variant),
calls Gemini with the subtopic's keywords + repr_docs to generate:
  label, summary (with inline citations), attitude, key_quotes.

Hard requirement: every claim in summary is cited to a specific document ID.

Input:  data/subtopics/overview.json          (reddit)
        data/subtopics_bluesky/overview.json  (bluesky)
Output: data/subtopics/grounded_summary.json
        data/subtopics_bluesky/grounded_summary.json

Usage:
    export GEMINI_API_KEY=...
    python grounded_summary.py                    # reddit
    python grounded_summary.py --platform bluesky
    python grounded_summary.py --platform all
    python grounded_summary.py --dry-run          # no API calls, verify logic
"""

import argparse
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

SYSTEM_PROMPT = """You are analyzing social media discussion about the Great Lakes for a university research project on environmental weak signals.

You will receive:
- A parent topic name (broad theme)
- Keywords characterizing a sub-topic cluster
- Up to 3 representative posts/comments from that cluster, each with an ID

Your task: output a single JSON object describing this sub-topic cluster, based ONLY on the provided documents.

Output schema (output raw JSON only — no markdown, no explanation):
{
  "label": "Short descriptive label (4-7 words)",
  "summary": "2-3 sentences describing what people in this cluster are discussing. Cite document IDs inline as [id] for every claim you make.",
  "attitude": "One concise phrase describing the dominant sentiment or stance (e.g. 'Concerned and alarmed', 'Nostalgic pride', 'Politically skeptical', 'Informational / neutral')",
  "key_quotes": [
    {"id": "<document id>", "quote": "<exact short phrase from the text, under 20 words>", "note": "<one sentence: why this quote is representative of the cluster>"}
  ]
}

Rules:
- Never invent facts not present in the provided documents
- key_quotes must use exact text from the documents (verbatim substring)
- summary citations must use IDs that appear in the input
- Include 2-3 key_quotes
- Output ONLY valid JSON, nothing else"""


def build_user_prompt(topic_name: str, subtopic: dict) -> str:
    lines = [
        f"Parent topic: {topic_name}",
        f"Sub-topic keywords: {', '.join(subtopic['keywords'][:8])}",
        f"Document count in cluster: {subtopic['doc_count']}",
        "",
        "Representative documents:",
    ]
    for doc in subtopic["repr_docs"]:
        lines.append(f"\n[{doc['id']}] (engagement score={doc['score']})")
        lines.append(doc["text"])
    return "\n".join(lines)


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return text


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_checkpoint(path: Path, data: dict):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def call_gemini(client, model_name: str, full_prompt: str) -> str:
    response = client.models.generate_content(
        model=model_name,
        contents=full_prompt,
    )
    return response.text


def process_platform(platform: str, client, model_name: str, dry_run: bool):
    if platform == "reddit":
        overview_path = Path("data/subtopics/overview.json")
        output_path = Path("data/subtopics/grounded_summary.json")
        ckpt_path = Path("data/subtopics/.grounded_checkpoint.json")
    elif platform == "mastodon":
        overview_path = Path("data/subtopics_mastodon/overview.json")
        output_path = Path("data/subtopics_mastodon/grounded_summary.json")
        ckpt_path = Path("data/subtopics_mastodon/.grounded_checkpoint.json")
    else:
        overview_path = Path("data/subtopics_bluesky/overview.json")
        output_path = Path("data/subtopics_bluesky/grounded_summary.json")
        ckpt_path = Path("data/subtopics_bluesky/.grounded_checkpoint.json")

    overview = json.loads(overview_path.read_text())
    checkpoint = load_checkpoint(ckpt_path)

    total = sum(t["n_subtopics"] for t in overview)
    print(f"[{platform}] {len(checkpoint)}/{total} already done")

    for topic in overview:
        topic_name = topic["topic_name"]
        for subtopic in topic["subtopics"]:
            key = f"{topic['topic_id']}_{subtopic['subtopic_id']}"
            if key in checkpoint:
                continue

            user_prompt = build_user_prompt(topic_name, subtopic)
            full_prompt = SYSTEM_PROMPT + "\n\n" + user_prompt

            if dry_run:
                print(f"  DRY [{key}] {topic_name[:50]}")
                checkpoint[key] = {
                    "label": "DRY RUN",
                    "summary": "dry run",
                    "attitude": "dry run",
                    "key_quotes": [],
                }
                continue

            for attempt in range(3):
                try:
                    text = call_gemini(client, model_name, full_prompt)
                    text = strip_fences(text)
                    result = json.loads(text)
                    checkpoint[key] = result
                    save_checkpoint(ckpt_path, checkpoint)
                    print(f"  [{key}] {result.get('label', '?')}")
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

    # Merge generated fields back into overview structure
    result_overview = []
    for topic in overview:
        topic_out = {**topic, "subtopics": []}
        for subtopic in topic["subtopics"]:
            key = f"{topic['topic_id']}_{subtopic['subtopic_id']}"
            generated = checkpoint.get(key, {})
            topic_out["subtopics"].append({**subtopic, "generated": generated})
        result_overview.append(topic_out)

    output_path.write_text(json.dumps(result_overview, ensure_ascii=False, indent=2))
    n = sum(len(t["subtopics"]) for t in result_overview)
    print(f"[{platform}] Written → {output_path}  ({n} subtopics)")


def main():
    parser = argparse.ArgumentParser(description="LLM-grounded sub-topic summaries")
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"], default="reddit")
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model ID (default: gemini-2.5-flash)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls; verify logic only")
    args = parser.parse_args()

    if not args.dry_run:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY is not set. Export it, or add GEMINI_API_KEY=... / GEMINI_KEY=... to .env")
        client = genai.Client(api_key=api_key)
    else:
        client = None

    platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
    for p in platforms:
        print(f"\n=== {p} ===")
        process_platform(p, client, args.model, args.dry_run)


if __name__ == "__main__":
    main()
