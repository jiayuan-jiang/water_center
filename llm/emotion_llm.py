"""
LLM-based emotion classification — replaces the j-hartmann distilroberta
classifier in analysis/sentiment_analysis.py, same motivation as llm/sentiment_llm.py
(manual review found the small RoBERTa models miss sarcasm/irony/implied
meaning). Companion to llm/sentiment_llm.py: same doc scope, same checkpoint/
provider pattern, separate output files so the RoBERTa-based emotion data
isn't overwritten until the LLM version is verified.

Input:  data/topics/documents_with_topics.csv | data/topics_bluesky/... | data/topics_mastodon/...
Output: data/analysis/emotion_llm_docs_{platform}.csv       (id, topic, emotion)
        data/analysis/emotion_llm_by_topic_{platform}.csv   (per-topic dominant + % breakdown)
        data/analysis/.emotion_llm_checkpoint_{platform}.json

Usage:
    python llm/emotion_llm.py --platform mastodon --provider deepseek
    python llm/emotion_llm.py --platform all --provider deepseek --workers 20
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

EMOTION_LABELS = ("neutral", "fear", "joy", "surprise", "sadness", "anger", "disgust")

SYSTEM_PROMPT = """You are classifying the dominant emotion expressed in a short social media comment about the Great Lakes region. Pay close attention to sarcasm, irony, rhetorical questions, and implied meaning — classify by the actual emotional intent behind the words, not just surface-level wording. Most comments are matter-of-fact and carry no strong emotion — use "neutral" for those rather than forcing a fit.

Output a single JSON object, nothing else:
{"emotion": "neutral" | "fear" | "joy" | "surprise" | "sadness" | "anger" | "disgust"}"""

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
            emotion = result.get("emotion")
            if emotion not in EMOTION_LABELS:
                raise ValueError(f"bad label: {emotion!r}")
            return doc_id, emotion, None
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
            emotion = result.get("emotion")
            if emotion not in EMOTION_LABELS:
                raise ValueError(f"bad label: {emotion!r}")
            return doc_id, emotion, None
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

    ckpt_path = Path(f"data/analysis/.emotion_llm_checkpoint_{platform}.json")
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
            doc_id, emotion, err = fut.result()
            if err:
                errors.append((doc_id, err))
                continue
            checkpoint[doc_id] = emotion
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
    df["emotion"] = df["id"].astype(str).map(checkpoint)
    labeled = df[df["emotion"].notna()]

    docs_out = labeled[["id", "topic", "emotion"]]
    docs_out.to_csv(f"data/analysis/emotion_llm_docs_{platform}.csv", index=False)
    print(f"[{platform}] written emotion_llm_docs_{platform}.csv ({len(docs_out):,} rows)")

    rows = []
    for topic, group in labeled.groupby("topic"):
        pct = (group["emotion"].value_counts(normalize=True) * 100).to_dict()
        dominant = max(pct, key=pct.get) if pct else "neutral"
        rows.append({
            "topic": topic,
            "n_docs": len(group),
            "dominant_emotion": dominant,
            **{f"pct_emotion_{k}": round(pct.get(k, 0.0), 1) for k in EMOTION_LABELS},
        })
    topic_out = pd.DataFrame(rows).sort_values("topic")
    topic_out.to_csv(f"data/analysis/emotion_llm_by_topic_{platform}.csv", index=False)
    print(f"[{platform}] written emotion_llm_by_topic_{platform}.csv ({len(topic_out)} topics)")


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
