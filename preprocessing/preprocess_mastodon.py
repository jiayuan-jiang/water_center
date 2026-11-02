"""
Clean and filter Mastodon posts for BERTopic analysis.
Input:  data/mastodon_raw.jsonl
Output: data/corpus_mastodon.jsonl  (one document per line, same schema as
        corpus.jsonl / corpus_bluesky.jsonl, plus an extra `url` field)

Kept separate from Reddit/Bluesky corpora — different platform, different
discourse style, never merged.
"""

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

INPUT     = Path("data/mastodon_raw.jsonl")
OUTPUT    = Path("data/corpus_mastodon.jsonl")
MIN_WORDS = 8  # same as Bluesky — short-form posts

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


def strip_html(content: str) -> str:
    text = re.sub(r"<br\s*/?>", " ", content)      # line breaks -> space
    text = re.sub(r"</p>", " ", text)               # paragraph breaks -> space
    text = re.sub(r"<[^>]+>", "", text)              # remaining tags
    text = html.unescape(text)
    return text


def clean_text(text: str) -> str:
    text = re.sub(r"https?://\S+", "", text)      # URLs
    text = re.sub(r"@\w+(@[\w.-]+)?", "", text)   # @mentions incl. @user@instance
    text = re.sub(r"#\w+", "", text)               # hashtags (already used to find the post)
    text = re.sub(r"\s{2,}", " ", text)           # extra whitespace
    return text.strip()


def is_english(record: dict) -> bool:
    lang = record.get("language")
    return lang is None or lang.lower() == "en"


def parse_utc(created_at: str) -> int:
    """ISO 8601 -> Unix timestamp."""
    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    return int(dt.timestamp())


def main():
    raw = [json.loads(l) for l in INPUT.open(encoding="utf-8")]
    print(f"Raw posts:             {len(raw):,}")

    # step 1: deduplicate by id
    seen_ids: set[str] = set()
    deduped = []
    for r in raw:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            deduped.append(r)
    print(f"After id dedup:        {len(deduped):,}  (-{len(raw)-len(deduped):,})")

    # step 2: language filter
    eng = [r for r in deduped if is_english(r)]
    print(f"After lang filter:     {len(eng):,}  (-{len(deduped)-len(eng):,})")

    # step 3: strip HTML + clean text
    for r in eng:
        r["text_clean"] = clean_text(strip_html(r["content"]))

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
            out = {
                "id":          r["id"],
                "post_id":     r.get("in_reply_to_id") or r["id"],
                "source":      "mastodon",
                "author":      r["account"]["acct"],
                "score":       r.get("favourites_count", 0),
                "created_utc": parse_utc(r["created_at"]),
                "text":        r["text_clean"],
                "url":         r["url"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"\nFinal corpus:          {len(final):,} documents")
    print(f"Output: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
