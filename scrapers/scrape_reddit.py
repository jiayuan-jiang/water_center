"""
Scrape Reddit posts via Arctic Shift API for Great Lakes horizon scan.

Strategy:
- r/greatlakes: fetch ALL posts (already on-topic)
- Regional/topic subreddits: filter by Great Lakes lake name keywords in title
- Time range: past 3 years
- Output: data/posts_raw.jsonl (one JSON object per line)
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

API_BASE = "https://arctic-shift.photon-reddit.com/api/posts/search"
OUTPUT_FILE = Path("data/posts_raw.jsonl")
REQUEST_DELAY = 2.0  # seconds between requests

# Unix timestamps for time range
NOW = int(datetime.now(timezone.utc).timestamp())
THREE_YEARS_AGO = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

# Subreddits to fetch WITHOUT keyword filter (already Great Lakes focused)
FOCUSED_SUBREDDITS = [
    "greatlakes",
    "GreatLakesWater",
]

# Subreddits to fetch WITH keyword filter
REGIONAL_SUBREDDITS = [
    "michigan",
    "wisconsin",
    "ohio",
    "ontario",
    "chicago",
    "minnesota",
    "illinois",
    "indiana",
    "environment",
    "waterquality",
    "sustainability",
    "ecology",
]

# Keywords to filter titles in regional subreddits (run as separate queries)
KEYWORDS = [
    "Great Lakes",
    "Lake Michigan",
    "Lake Erie",
    "Lake Superior",
    "Lake Huron",
    "Lake Ontario",
]


def fetch_posts(subreddit: str, title_filter: Optional[str], after: int, before: int) -> list[dict]:
    """Fetch one page of posts from Arctic Shift API (returns newest-first)."""
    params = {
        "subreddit": subreddit,
        "after": after,
        "before": before,
        "limit": 100,
    }
    if title_filter:
        params["title"] = title_filter

    try:
        resp = requests.get(API_BASE, params=params, timeout=30)
        resp.raise_for_status()
        return resp.json().get("data") or []
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            print(f"  [429] Rate limited, waiting 30s...")
            time.sleep(30)
            return fetch_posts(subreddit, title_filter, after, before)
        print(f"  [ERROR] {e}")
        return []
    except requests.RequestException as e:
        print(f"  [ERROR] {e}")
        return []


def scrape(subreddit: str, title_filter: Optional[str], seen_ids: set, out_file) -> int:
    """Paginate through all posts (newest→oldest) for a subreddit/keyword combo."""
    label = f"r/{subreddit}" + (f" + '{title_filter}'" if title_filter else " (all)")
    print(f"\nScraping {label} ...")

    count = 0
    before_cursor = NOW  # walk backwards in time

    while True:
        posts = fetch_posts(subreddit, title_filter, after=THREE_YEARS_AGO, before=before_cursor)
        if not posts:
            break

        new_posts = [p for p in posts if p.get("id") not in seen_ids]
        for post in new_posts:
            seen_ids.add(post["id"])
            out_file.write(json.dumps(post, ensure_ascii=False) + "\n")

        count += len(new_posts)
        oldest_ts = posts[-1].get("created_utc", before_cursor)
        print(f"  fetched {len(posts)} posts | oldest: {datetime.fromtimestamp(oldest_ts).strftime('%Y-%m-%d')} | total new: {count}")

        if len(posts) < 100:
            break  # last page

        before_cursor = oldest_ts - 1
        time.sleep(REQUEST_DELAY)

    return count


def main():
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    seen_ids: set[str] = set()
    total = 0

    # Load already-scraped IDs if resuming
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"Resuming — {len(seen_ids)} posts already collected.")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        # Focused subreddits: no keyword filter
        for sub in FOCUSED_SUBREDDITS:
            total += scrape(sub, None, seen_ids, out)

        # Regional subreddits: one query per keyword
        for sub in REGIONAL_SUBREDDITS:
            for kw in KEYWORDS:
                total += scrape(sub, kw, seen_ids, out)
                time.sleep(REQUEST_DELAY)

    print(f"\nDone. Total new posts collected: {total}")
    print(f"Output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
