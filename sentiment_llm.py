"""
LLM-based sentiment classification — replaces the cardiffnlp RoBERTa classifier
in sentiment_analysis.py after manual review (2026-07-31) found it misses
sarcasm, irony, and implied meaning on many comments. Full corpus: ~54,310 docs
across both platforms (Reddit 4,724 + Bluesky 49,586, same topic-filtered set
as sentiment_analysis.py).

Cost: ~$1.23 total estimated at gpt-4o-mini rates (precise tiktoken count on a
sample — see conversation). Concurrency, not cost, is the real constraint here:
54K+ calls is too many to run serially like the 62-call controversy_llm.py, so
this uses a thread pool, and checkpoints every FLUSH_EVERY completions (not
every single one — rewriting a 54K-entry JSON file per completion would make
the I/O itself the bottleneck) so a crash or Ctrl-C loses at most one flush
interval of progress; already-done ids are skipped on rerun.

Input:  data/topics/documents_with_topics.csv | data/topics_bluesky/documents_with_topics.csv
Output: data/analysis/sentiment_llm_docs_{platform}.csv       (id, sentiment)
        data/analysis/sentiment_llm_by_topic_{platform}.csv   (per-topic % breakdown)
        data/analysis/.sentiment_llm_checkpoint_{platform}.json

Kept separate from sentiment_analysis.py's RoBERTa-based output files for
comparison, not overwritten.

Reads OPENAI_API_KEY from environment or .env.

Usage:
    python sentiment_llm.py --platform reddit
    python sentiment_llm.py --platform all --workers 20
    python sentiment_llm.py --platform reddit --limit 100   # pilot run
"""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI

from grounded_summary import load_checkpoint, save_checkpoint, strip_fences

VALID_BLUESKY_TOPICS = {
    0, 1, 4, 5, 10, 13, 15, 18, 19, 26, 27, 28, 29, 31,
    32, 33, 35, 36, 39, 41, 43, 45, 46, 48, 49, 50, 53, 59,
}

VALID_MASTODON_TOPICS = {0, 1, 2, 4, 5, 6, 8, 10, 11, 12, 14, 15, 17, 21, 22, 24}

SYSTEM_PROMPT = """You are classifying the sentiment of a short social media comment about the Great Lakes region. Pay close attention to sarcasm, irony, rhetorical questions, and implied meaning — classify by the actual intent behind the words, not just surface-level positive/negative wording.

Output a single JSON object, nothing else:
{"sentiment": "positive" | "neutral" | "negative"}"""

FLUSH_EVERY = 200


def load_docs(platform: str) -> pd.DataFrame:
    if platform == "bluesky":
        df = pd.read_csv("data/topics_bluesky/documents_with_topics.csv")
        df = df[df["topic"].isin(VALID_BLUESKY_TOPICS)]
    elif platform == "mastodon":
        df = pd.read_csv("data/topics_mastodon/documents_with_topics.csv")
        df = df[df["topic"].isin(VALID_MASTODON_TOPICS)]
    else:
        df = pd.read_csv("data/topics/documents_with_topics.csv")
        df = df[df["topic"] != -1]
    return df[["id", "topic", "text"]].copy()


def classify_one_openai(client, model_name, doc_id, text):
    text = "" if pd.isna(text) else str(text)[:600]
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            result = json.loads(resp.choices[0].message.content)
            sentiment = result.get("sentiment")
            if sentiment not in ("positive", "neutral", "negative"):
                raise ValueError(f"bad label: {sentiment!r}")
            return doc_id, sentiment, None
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                time.sleep(5 * (attempt + 1))
            elif attempt == 2:
                return doc_id, None, str(e)
    return doc_id, None, "max retries exceeded"


GEMINI_CONFIG = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_budget=0))


def classify_one_gemini(client, model_name, doc_id, text):
    text = "" if pd.isna(text) else str(text)[:600]
    full_prompt = SYSTEM_PROMPT + "\n\nComment:\n" + text
    for attempt in range(3):
        try:
            resp = client.models.generate_content(
                model=model_name, contents=full_prompt, config=GEMINI_CONFIG,
            )
            result = json.loads(strip_fences(resp.text))
            sentiment = result.get("sentiment")
            if sentiment not in ("positive", "neutral", "negative"):
                raise ValueError(f"bad label: {sentiment!r}")
            return doc_id, sentiment, None
        except Exception as e:
            if "quota" in str(e).lower() or "rate" in str(e).lower() or "429" in str(e):
                time.sleep(5 * (attempt + 1))
            elif attempt == 2:
                return doc_id, None, str(e)
    return doc_id, None, "max retries exceeded"


def process_platform(platform: str, client, provider: str, model_name: str, workers: int, limit: int | None):
    classify_one = classify_one_gemini if provider == "gemini" else classify_one_openai
    df = load_docs(platform)
    if limit:
        df = df.head(limit)

    ckpt_path = Path(f"data/analysis/.sentiment_llm_checkpoint_{platform}.json")
    checkpoint = load_checkpoint(ckpt_path)
    todo = [(str(r.id), r.text) for r in df.itertuples() if str(r.id) not in checkpoint]
    print(f"[{platform}] {len(checkpoint)}/{len(df)} already done, {len(todo)} to go "
          f"({workers} workers, provider={provider})")

    errors = []
    completed_since_flush = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(classify_one, client, model_name, doc_id, text): doc_id
                   for doc_id, text in todo}
        for i, fut in enumerate(as_completed(futures), 1):
            doc_id, sentiment, err = fut.result()
            if err:
                errors.append((doc_id, err))
                continue
            checkpoint[doc_id] = sentiment
            completed_since_flush += 1
            if completed_since_flush >= FLUSH_EVERY:
                save_checkpoint(ckpt_path, checkpoint)
                completed_since_flush = 0
                rate = i / (time.time() - t0)
                print(f"  [{platform}] {len(checkpoint)}/{len(df)} done "
                      f"({rate:.1f} docs/sec, {len(errors)} errors)")

    save_checkpoint(ckpt_path, checkpoint)
    print(f"[{platform}] finished: {len(checkpoint)} labeled, {len(errors)} errors")
    if errors:
        print(f"  first few errors: {errors[:5]}")

    # ── write outputs ──
    df["sentiment"] = df["id"].astype(str).map(checkpoint)
    labeled = df[df["sentiment"].notna()]

    docs_out = labeled[["id", "topic", "sentiment"]]
    docs_out.to_csv(f"data/analysis/sentiment_llm_docs_{platform}.csv", index=False)
    print(f"[{platform}] written sentiment_llm_docs_{platform}.csv ({len(docs_out):,} rows)")

    rows = []
    for topic, group in labeled.groupby("topic"):
        pct = (group["sentiment"].value_counts(normalize=True) * 100).to_dict()
        rows.append({
            "topic": topic,
            "n_docs": len(group),
            "pct_positive": round(pct.get("positive", 0.0), 1),
            "pct_neutral": round(pct.get("neutral", 0.0), 1),
            "pct_negative": round(pct.get("negative", 0.0), 1),
        })
    topic_out = pd.DataFrame(rows).sort_values("topic")
    topic_out.to_csv(f"data/analysis/sentiment_llm_by_topic_{platform}.csv", index=False)
    print(f"[{platform}] written sentiment_llm_by_topic_{platform}.csv ({len(topic_out)} topics)")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"], default="reddit")
    parser.add_argument("--provider", choices=["openai", "gemini", "deepseek"], default="openai")
    parser.add_argument("--model", default=None,
                         help="default: gpt-4o-mini (openai) / gemini-2.5-flash (gemini) / deepseek-chat (deepseek)")
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--limit", type=int, default=None, help="cap doc count, for pilot runs")
    args = parser.parse_args()

    load_dotenv()
    if args.provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_KEY")
        if not api_key:
            raise SystemExit("GEMINI_API_KEY is not set. Export it, or add GEMINI_API_KEY=... / GEMINI_KEY=... to .env")
        client = genai.Client(api_key=api_key)
        model_name = args.model or "gemini-2.5-flash"
    elif args.provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("DEEPSEEK_KEY")
        if not api_key:
            raise SystemExit("DEEPSEEK_API_KEY is not set. Add DEEPSEEK_API_KEY=... / DEEPSEEK_KEY=... to .env")
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        model_name = args.model or "deepseek-chat"
    else:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY is not set (env or .env)")
        client = OpenAI(api_key=api_key)
        model_name = args.model or "gpt-4o-mini"

    platforms = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
    for p in platforms:
        print(f"\n=== {p} ({args.provider}/{model_name}) ===")
        process_platform(p, client, args.provider, model_name, args.workers, args.limit)


if __name__ == "__main__":
    main()
