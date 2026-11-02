"""
Clean and filter Bluesky posts for BERTopic analysis.
Input:  data/bluesky_raw.jsonl
Output: data/corpus_bluesky.jsonl  (one document per line, same schema as corpus.jsonl)

Kept separate from Reddit corpus — different platform, different discourse style.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

INPUT    = Path("data/bluesky_raw.jsonl")
OUTPUT   = Path("data/corpus_bluesky.jsonl")
MIN_WORDS = 8  # lower than Reddit's 15 — Bluesky posts are capped at 300 chars

KEEP_KEYWORDS = [
    "water", "lake", "river", "shore", "beach", "fish", "fishing",
    "algae", "algal", "pfas", "phosphorus", "nutrient", "pollution",
    "invasive", "carp", "lamprey", "mussel", "flooding", "drought",
    "watershed", "wetland", "ecosystem", "environment", "climate",
    "drinking water", "water quality", "water level", "swimming",
    "great lakes", "lake michigan", "lake erie", "lake superior",
    "lake huron", "lake ontario",
]


def is_relevant(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEEP_KEYWORDS)


def is_english(record: dict) -> bool:
    langs = record.get("langs")
    if not langs:
        return True  # no lang tag — keep and let content decide
    return "en" in [l.lower()[:2] for l in langs]


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)      # URLs
    text = re.sub(r"@\w+", "", text)              # @mentions
    text = re.sub(r"\s{2,}", " ", text)           # extra whitespace
    return text.strip()


def parse_utc(created_at: str) -> int:
    """ISO 8601 → Unix timestamp."""
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return int(dt.timestamp())


def main():
    raw = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"Raw posts:             {len(raw):,}")

    # step 1: deduplicate by URI
    seen_uris: set[str] = set()
    deduped = []
    for r in raw:
        if r["uri"] not in seen_uris:
            seen_uris.add(r["uri"])
            deduped.append(r)
    print(f"After URI dedup:       {len(deduped):,}  (-{len(raw)-len(deduped):,})")

    # step 2: language filter (skip explicitly non-English)
    eng = [r for r in deduped if is_english(r)]
    print(f"After lang filter:     {len(eng):,}  (-{len(deduped)-len(eng):,})")

    # step 3: clean text
    for r in eng:
        r["text_clean"] = clean_text(r["text"])

    # step 4: minimum word count
    long_enough = [r for r in eng if len(r["text_clean"].split()) >= MIN_WORDS]
    print(f"After length filter:   {len(long_enough):,}  (min {MIN_WORDS} words)")

    # step 5: keyword relevance
    relevant = [r for r in long_enough if is_relevant(r["text_clean"])]
    print(f"After relevance filter:{len(relevant):,}")

    # step 6: exact-text dedup
    seen_texts: set[str] = set()
    final = []
    for r in relevant:
        t = r["text_clean"].lower()
        if t not in seen_texts:
            seen_texts.add(t)
            final.append(r)
    print(f"After text dedup:      {len(final):,}  (-{len(relevant)-len(final):,})")

    # write output
    with OUTPUT.open("w", encoding="utf-8") as f:
        for r in final:
            rkey = r["uri"].split("/")[-1]
            out = {
                "id":          rkey,
                "post_id":     r.get("root_uri") or rkey,
                "source":      "bluesky",
                "author":      r["author_handle"],
                "score":       r["like_count"],
                "created_utc": parse_utc(r["created_at"]),
                "text":        r["text_clean"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"\nFinal corpus:          {len(final):,} documents")
    print(f"Output: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()