"""
Fetch comments for all posts in posts_raw.jsonl via Arctic Shift API.
Skips posts with 0 comments. Resumes from checkpoint on re-run.
Output: data/comments_raw.jsonl
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

API_BASE = "https://arctic-shift.photon-reddit.com/api/comments/search"
POSTS_FILE = Path("data/posts_raw.jsonl")
COMMENTS_FILE = Path("data/comments_raw.jsonl")
CHECKPOINT_FILE = Path("data/comments_checkpoint.txt")
REQUEST_DELAY = 2.0


def fetch_comments(post_id: str, before: Optional[int] = None) -> list[dict]:
    params = {"link_id": f"t3_{post_id}", "limit": 100}
    if before:
        params["before"] = before
    for attempt in range(5):
        try:
            resp = requests.get(API_BASE, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  [429] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("data") or []
        except requests.RequestException as e:
            print(f"  [ERROR] attempt {attempt+1}: {e}")
            time.sleep(10)
    return []


def fetch_all_comments_for_post(post_id: str, num_comments: int) -> list[dict]:
    all_comments = []
    seen_ids = set()
    before = None

    while True:
        batch = fetch_comments(post_id, before)
        if not batch:
            break

        new = [c for c in batch if c.get("id") not in seen_ids]
        for c in new:
            seen_ids.add(c["id"])
        all_comments.extend(new)

        if len(batch) < 100:
            break

        before = batch[-1].get("created_utc", 0) - 1
        time.sleep(REQUEST_DELAY)

    return all_comments


def load_done_ids() -> set:
    if CHECKPOINT_FILE.exists():
        return set(CHECKPOINT_FILE.read_text().splitlines())
    return set()


def main():
    COMMENTS_FILE.parent.mkdir(exist_ok=True)

    posts = [json.loads(l) for l in POSTS_FILE.open()]
    # prioritize most-discussed posts first
    posts = sorted(posts, key=lambda p: p.get("num_comments", 0), reverse=True)
    posts_with_comments = [p for p in posts if p.get("num_comments", 0) > 0]

    done_ids = load_done_ids()
    todo = [p for p in posts_with_comments if p["id"] not in done_ids]

    print(f"Posts with comments: {len(posts_with_comments)}")
    print(f"Already done:        {len(done_ids)}")
    print(f"Remaining:           {len(todo)}")

    total_comments = 0

    with COMMENTS_FILE.open("a", encoding="utf-8") as out, \
         CHECKPOINT_FILE.open("a") as ckpt:

        for i, post in enumerate(todo, 1):
            pid = post["id"]
            expected = post.get("num_comments", 0)
            sub = post.get("subreddit", "?")

            comments = fetch_all_comments_for_post(pid, expected)
            for c in comments:
                c["_post_id"] = pid
                out.write(json.dumps(c, ensure_ascii=False) + "\n")

            total_comments += len(comments)
            ckpt.write(pid + "\n")
            ckpt.flush()
            out.flush()

            if i % 10 == 0 or i == len(todo):
                print(f"  [{i}/{len(todo)}] r/{sub} post {pid} — {len(comments)} comments | total so far: {total_comments:,}")

            time.sleep(REQUEST_DELAY)

    print(f"\nDone. Total comments collected: {total_comments:,}")
    print(f"Output: {COMMENTS_FILE.resolve()}")


if __name__ == "__main__":
    main()
