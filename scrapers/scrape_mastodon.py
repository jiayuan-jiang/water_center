"""
Scrape Mastodon (mastodon.social) hashtag timelines for Great Lakes horizon scan.

Strategy:
- No global full-text search exists on Mastodon (see experiments/scrape_mastodon_test.py
  findings) - the only public, unauthenticated way to find relevant posts is
  hashtag timelines, which also surface federated posts from other instances.
- Time range: past 3 years, same cutoff as scrapers/scrape_reddit.py / scrapers/scrape_bluesky.py
- Pagination: ID-based (max_id), walking backwards in time, since Mastodon
  timelines have no since/until timestamp params like Arctic Shift.
- Output: data/mastodon_raw.jsonl (one JSON object per line, raw API objects)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

INSTANCE = "https://mastodon.social"
OUTPUT_FILE = Path("data/mastodon_raw.jsonl")
CHECKPOINT_FILE = Path("data/mastodon_checkpoint.json")
REQUEST_DELAY = 1.5  # seconds between requests
PAGE_LIMIT = 40  # Mastodon max per page

THREE_YEARS_AGO = datetime(2023, 1, 1, tzinfo=timezone.utc)

HASHTAGS = [
    "greatlakes",
    "lakemichigan",
    "lakeerie",
    "lakesuperior",
    "lakehuron",
    "lakeontario",
    "greatlakeswater",
    "greatlakesecho",
    "greatlakeswatercompact",
    "greatlakeswatershedcleanup",
    "michigan",
    "wisconsin",
    "ohio",
    "ontario",
    "chicago",
    "minnesota",
    "illinois",
    "indiana",
]


def parse_created_at(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text())
    return {}


def save_checkpoint(checkpoint: dict) -> None:
    CHECKPOINT_FILE.write_text(json.dumps(checkpoint, indent=2))


def fetch_tag_page(hashtag: str, max_id: Optional[str]) -> list[dict]:
    params = {"limit": PAGE_LIMIT}
    if max_id:
        params["max_id"] = max_id
    try:
        resp = requests.get(
            f"{INSTANCE}/api/v1/timelines/tag/{hashtag}", params=params, timeout=30
        )
        resp.raise_for_status()
        return resp.json() or []
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            print("  [429] Rate limited, waiting 30s...")
            time.sleep(30)
            return fetch_tag_page(hashtag, max_id)
        print(f"  [ERROR] {e}")
        return []
    except requests.RequestException as e:
        print(f"  [ERROR] {e}")
        return []


def scrape_hashtag(hashtag: str, seen_ids: set, out_file, checkpoint: dict) -> int:
    state = checkpoint.setdefault(hashtag, {"max_id": None, "done": False})
    if state["done"]:
        print(f"\n#{hashtag}: already done (checkpoint), skipping")
        return 0

    print(f"\nScraping #{hashtag} ...")
    count = 0
    max_id = state["max_id"]

    while True:
        posts = fetch_tag_page(hashtag, max_id)
        if not posts:
            state["done"] = True
            save_checkpoint(checkpoint)
            break

        cutoff_hit = False
        for post in posts:
            created = parse_created_at(post["created_at"])
            if created < THREE_YEARS_AGO:
                cutoff_hit = True
                break
            if post["id"] not in seen_ids:
                seen_ids.add(post["id"])
                post["_hashtag_query"] = hashtag
                out_file.write(json.dumps(post, ensure_ascii=False) + "\n")
                out_file.flush()
                count += 1

        oldest = posts[-1]["created_at"]
        print(f"  fetched {len(posts)} posts | oldest: {oldest} | total new: {count}")

        max_id = posts[-1]["id"]
        state["max_id"] = max_id
        if cutoff_hit or len(posts) < PAGE_LIMIT:
            state["done"] = True
            save_checkpoint(checkpoint)
            break

        save_checkpoint(checkpoint)
        time.sleep(REQUEST_DELAY)

    return count


def main():
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    seen_ids: set[str] = set()
    total = 0

    checkpoint = load_checkpoint()
    if checkpoint:
        print(f"Checkpoint loaded: {sum(1 for s in checkpoint.values() if s['done'])}/"
              f"{len(checkpoint)} hashtags marked done")

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            for line in f:
                try:
                    seen_ids.add(json.loads(line)["id"])
                except Exception:
                    pass
        print(f"Resuming — {len(seen_ids)} posts already collected.")

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out:
        for hashtag in HASHTAGS:
            total += scrape_hashtag(hashtag, seen_ids, out, checkpoint)
            time.sleep(REQUEST_DELAY)

    print(f"\nDone. Total new posts collected: {total}")
    print(f"Output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
