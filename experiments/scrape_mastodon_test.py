"""
Feasibility probe for Mastodon (mastodon.social) as a third data source.

Not a production scraper - just checks how much Great Lakes-relevant content
is reachable via public hashtag timelines, and confirms the search API's
auth requirement, before deciding whether to build scrapers/scrape_mastodon.py.

Output: data/mastodon_test_raw.jsonl (throwaway, not wired into corpus.jsonl)
"""

import json
import time
from pathlib import Path

import requests

INSTANCE = "https://mastodon.social"
OUTPUT_FILE = Path("data/mastodon_test_raw.jsonl")
REQUEST_DELAY = 1.0  # seconds between requests
PAGE_LIMIT = 40  # Mastodon max per page
PROBE_CAP = 500  # stop a hashtag early once we've seen this many posts

HASHTAGS = [
    "greatlakes",
    "lakeerie",
    "lakemichigan",
    "lakesuperior",
    "lakehuron",
    "lakeontario",
]


def check_search_requires_auth() -> None:
    print("Checking GET /api/v2/search (unauthenticated) ...")
    try:
        resp = requests.get(
            f"{INSTANCE}/api/v2/search",
            params={"q": "Lake Erie", "type": "statuses"},
            timeout=15,
        )
        print(f"  status={resp.status_code} body={resp.text[:200]!r}")
    except requests.RequestException as e:
        print(f"  [ERROR] {e}")


def fetch_tag_page(hashtag: str, max_id: str | None) -> list[dict]:
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


def scrape_hashtag(hashtag: str, out_file) -> list[dict]:
    print(f"\nScraping #{hashtag} ...")
    collected: list[dict] = []
    max_id = None

    while len(collected) < PROBE_CAP:
        posts = fetch_tag_page(hashtag, max_id)
        if not posts:
            break

        for post in posts:
            post["_probe_hashtag"] = hashtag
            out_file.write(json.dumps(post, ensure_ascii=False) + "\n")
        collected.extend(posts)

        print(
            f"  fetched {len(posts)} posts | oldest so far: {posts[-1].get('created_at')} "
            f"| total: {len(collected)}"
        )

        if len(posts) < PAGE_LIMIT:
            break  # last page

        max_id = posts[-1]["id"]
        time.sleep(REQUEST_DELAY)

    return collected


def summarize(hashtag: str, posts: list[dict]) -> None:
    print(f"\n=== #{hashtag}: {len(posts)} posts ===")
    if not posts:
        print("  (no results)")
        return

    dates = [p.get("created_at") for p in posts if p.get("created_at")]
    accounts = {p.get("account", {}).get("acct") for p in posts}
    print(f"  date range: {min(dates)} -> {max(dates)}")
    print(f"  distinct accounts: {len(accounts)}")
    print("  sample posts:")
    for post in posts[:5]:
        acct = post.get("account", {}).get("acct")
        content = post.get("content", "")
        # strip HTML tags crudely for a readable console preview
        text = content.replace("<p>", "").replace("</p>", " ").replace("<br />", " ")
        print(f"    [{acct}] {text[:160]}")


def main():
    OUTPUT_FILE.parent.mkdir(exist_ok=True)

    check_search_requires_auth()

    all_results: dict[str, list[dict]] = {}
    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for hashtag in HASHTAGS:
            all_results[hashtag] = scrape_hashtag(hashtag, out)
            time.sleep(REQUEST_DELAY)

    print("\n\n########## SUMMARY ##########")
    total = 0
    for hashtag, posts in all_results.items():
        summarize(hashtag, posts)
        total += len(posts)

    print(f"\nTotal posts collected across {len(HASHTAGS)} hashtags: {total}")
    print(f"Output: {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
