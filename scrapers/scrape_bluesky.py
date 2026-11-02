"""
Scrape Bluesky posts via atproto searchPosts for Great Lakes horizon scan.

Strategy:
- 12 queries per month: exact-phrase ("Great Lakes") + hashtag (#GreatLakes) for each lake
- Monthly time windows (2023-01 to today) + cursor pagination within each window
- URI-based dedup covers overlap across queries
- Checkpoint resumes interrupted runs

Usage:
    export BSKY_USER=jiayuanj@umich.edu
    export BSKY_PASS=<app-password>
    python scrapers/scrape_bluesky.py
"""

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from atproto import Client
from atproto_client.exceptions import BadRequestError, NetworkError

# load .env if present
_env = Path(__file__).resolve().parent.parent / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

OUTPUT_FILE     = Path("data/bluesky_raw.jsonl")
CHECKPOINT_FILE = Path("data/bluesky_checkpoint.json")
START_DATE      = date(2023, 1, 1)
REQUEST_DELAY   = 0.5  # seconds between pages

# Exact-phrase and hashtag queries — kept separate because results don't fully overlap
QUERIES = [
    # exact phrase (matches body text)
    '"Great Lakes"',
    '"Lake Michigan"',
    '"Lake Erie"',
    '"Lake Superior"',
    '"Lake Huron"',
    '"Lake Ontario"',
    # hashtag (matches tagged posts, not always caught by phrase search)
    '#GreatLakes',
    '#LakeMichigan',
    '#LakeErie',
    '#LakeSuperior',
    '#LakeHuron',
    '#LakeOntario',
]


def month_windows(start: date, end: date):
    """Yield (since_str, until_str, month_label) for each calendar month."""
    cur = start.replace(day=1)
    while cur <= end:
        if cur.month == 12:
            nxt = cur.replace(year=cur.year + 1, month=1)
        else:
            nxt = cur.replace(month=cur.month + 1)
        last_day = nxt - timedelta(days=1)
        yield (
            cur.strftime("%Y-%m-%dT00:00:00Z"),
            last_day.strftime("%Y-%m-%dT23:59:59Z"),
            cur.strftime("%Y-%m"),
        )
        cur = nxt


def load_checkpoint() -> set:
    if CHECKPOINT_FILE.exists():
        data = json.loads(CHECKPOINT_FILE.read_text())
        return set(map(tuple, data.get("done", [])))
    return set()


def save_checkpoint(done: set) -> None:
    CHECKPOINT_FILE.write_text(
        json.dumps({"done": [list(pair) for pair in sorted(done)]}, indent=2)
    )


def load_seen_uris() -> set:
    if not OUTPUT_FILE.exists():
        return set()
    seen = set()
    with OUTPUT_FILE.open() as f:
        for line in f:
            try:
                seen.add(json.loads(line)["uri"])
            except Exception:
                pass
    return seen


def post_to_record(post, query: str) -> dict:
    r = post.record
    reply = getattr(r, "reply", None)
    return {
        "uri":           post.uri,
        "author_handle": post.author.handle,
        "author_did":    post.author.did,
        "created_at":    r.created_at,
        "text":          r.text,
        "langs":         getattr(r, "langs", None),
        "like_count":    post.like_count or 0,
        "reply_count":   post.reply_count or 0,
        "repost_count":  post.repost_count or 0,
        "is_reply":      reply is not None,
        "parent_uri":    reply.parent.uri if reply else None,
        "root_uri":      reply.root.uri if reply else None,
        "query":         query,
    }


def search_window(client: Client, query: str, since: str, until: str,
                  seen_uris: set, out_file) -> int:
    count = 0
    cursor = None
    while True:
        params = {"q": query, "since": since, "until": until, "limit": 100}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = client.app.bsky.feed.search_posts(params=params)
        except BadRequestError as e:
            print(f"    [BadRequest] {e} — skipping window")
            break
        except NetworkError as e:
            print(f"    [NetworkError] {e} — retrying in 10s")
            time.sleep(10)
            continue
        except Exception as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code == 429:
                print("    [429] Rate limited — waiting 30s")
                time.sleep(30)
                continue
            print(f"    [ERROR] {e} — skipping window")
            break

        posts = resp.posts or []
        for post in posts:
            if post.uri in seen_uris:
                continue
            seen_uris.add(post.uri)
            out_file.write(json.dumps(post_to_record(post, query), ensure_ascii=False) + "\n")
            count += 1

        if not resp.cursor:
            break
        cursor = resp.cursor
        time.sleep(REQUEST_DELAY)

    return count


def main():
    handle   = os.environ.get("BSKY_USER", "").strip()
    password = os.environ.get("BSKY_PASS", "").strip()
    if not handle or not password:
        print("ERROR: set BSKY_USER and BSKY_PASS environment variables.")
        sys.exit(1)

    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    done      = load_checkpoint()
    seen_uris = load_seen_uris()
    print(f"Checkpoint: {len(done)} (query, month) pairs already done")
    print(f"Existing posts in output: {len(seen_uris):,}")

    client = Client()
    client.login(handle, password)
    print(f"Logged in as: {handle}\n")

    windows = list(month_windows(START_DATE, date.today()))
    total_queries = len(QUERIES) * len(windows)
    completed = len(done)
    total_new = 0

    with OUTPUT_FILE.open("a", encoding="utf-8") as out:
        for query in QUERIES:
            q_new = 0
            for since, until, month in windows:
                if (query, month) in done:
                    completed += 0  # already counted
                    continue

                new = search_window(client, query, since, until, seen_uris, out)
                q_new += new
                total_new += new
                done.add((query, month))
                save_checkpoint(done)
                completed += 1

                print(f"  [{query}] {month}: +{new:3d} posts  ({completed}/{total_queries} windows done)")
                time.sleep(REQUEST_DELAY)

            print(f"  → query '{query}' subtotal: {q_new}\n")

    print(f"Done. Total new posts collected: {total_new:,}")
    print(f"Output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
