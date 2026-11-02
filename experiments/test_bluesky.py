"""
Minimal test: can Bluesky searchPosts return results from 2023?
Tests each keyword, prints oldest post date found.

Usage:
    BSKY_USER=you.bsky.social BSKY_PASS=yourpassword python experiments/test_bluesky.py
"""

import os
import sys
import time
from atproto import Client

KEYWORDS = [
    "Great Lakes",
    "Lake Michigan",
    "Lake Erie",
    "Lake Superior",
    "Lake Huron",
    "Lake Ontario",
]

handle   = os.environ.get("BSKY_USER", "").strip()
password = os.environ.get("BSKY_PASS", "").strip()

if not handle or not password:
    print("ERROR: set BSKY_USER and BSKY_PASS environment variables.")
    print("  export BSKY_USER=you.bsky.social")
    print("  export BSKY_PASS=yourpassword")
    sys.exit(1)

client = Client()
client.login(handle, password)
print(f"Logged in as: {handle}")

print("=" * 60)
print("Bluesky searchPosts — historical depth test")
print("=" * 60)

for kw in KEYWORDS:
    print(f"\nKeyword: \"{kw}\"")
    try:
        resp = client.app.bsky.feed.search_posts(
            params={"q": kw, "limit": 100, "sort": "oldest"}
        )
        posts = resp.posts if resp.posts else []
        if not posts:
            print("  → 0 results")
            continue

        dates = [p.record.created_at for p in posts if hasattr(p, "record")]
        dates.sort()
        print(f"  → {len(posts)} posts returned")
        print(f"     oldest : {dates[0] if dates else 'n/a'}")
        print(f"     newest : {dates[-1] if dates else 'n/a'}")

    except Exception as e:
        print(f"  → ERROR: {e}")

    time.sleep(1)

print("\n" + "=" * 60)
print("Test complete.")
