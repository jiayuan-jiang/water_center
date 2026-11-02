"""
Clean and filter Reddit comments for BERTopic analysis.
Input:  data/comments_raw.jsonl
Output: data/corpus.jsonl  (one document per line)
"""

import json
import re
from pathlib import Path

INPUT  = Path("data/comments_raw.jsonl")
OUTPUT = Path("data/corpus.jsonl")
MIN_WORDS = 15

DELETED = {"[deleted]", "[removed]", "", None}

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

def clean_text(text: str) -> str:
    # remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)
    # remove Reddit markdown
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)   # bold / italic
    text = re.sub(r"~~(.+?)~~", r"\1", text)               # strikethrough
    text = re.sub(r"^>+\s?", "", text, flags=re.MULTILINE) # blockquotes
    text = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", text)        # hyperlinks
    text = re.sub(r"#{1,6}\s", "", text)                   # headers
    text = re.sub(r"`{1,3}.*?`{1,3}", "", text, flags=re.DOTALL)  # code blocks
    text = re.sub(r"\n{2,}", " ", text)                    # multiple newlines
    text = re.sub(r"\s{2,}", " ", text)                    # multiple spaces
    return text.strip()

def main():
    raw = [json.loads(l) for l in INPUT.open()]
    print(f"Raw comments:         {len(raw):,}")

    # step 1: remove deleted/removed
    valid = [c for c in raw if c.get("body") not in DELETED]
    print(f"After deleted filter: {len(valid):,}  (-{len(raw)-len(valid):,})")

    # step 2: clean text
    for c in valid:
        c["body_clean"] = clean_text(c["body"])

    # step 3: remove too short
    valid = [c for c in valid if len(c["body_clean"].split()) >= MIN_WORDS]
    print(f"After length filter:  {len(valid):,}  (min {MIN_WORDS} words)")

    # step 4: keyword relevance filter
    valid = [c for c in valid if is_relevant(c["body_clean"])]
    print(f"After relevance filter:{len(valid):,}")

    # step 5: deduplicate by exact text
    seen_texts = set()
    deduped = []
    for c in valid:
        t = c["body_clean"].lower()
        if t not in seen_texts:
            seen_texts.add(t)
            deduped.append(c)
    print(f"After dedup:          {len(deduped):,}  (-{len(valid)-len(deduped):,})")

    # write output
    with OUTPUT.open("w", encoding="utf-8") as f:
        for c in deduped:
            out = {
                "id":         c.get("id"),
                "post_id":    c.get("_post_id"),
                "subreddit":  c.get("subreddit"),
                "author":     c.get("author"),
                "score":      c.get("score"),
                "created_utc":c.get("created_utc"),
                "text":       c["body_clean"],
            }
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(f"\nFinal corpus:         {len(deduped):,} documents")
    print(f"Output: {OUTPUT.resolve()}")

if __name__ == "__main__":
    main()
