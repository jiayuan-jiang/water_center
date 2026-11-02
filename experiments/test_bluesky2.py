"""
Test 2: try since/until params and oldest sort to probe historical depth.
"""

import os, sys, time
from atproto import Client

client = Client()
client.login(os.environ["BSKY_USER"], os.environ["BSKY_PASS"])

KW = "Great Lakes"

tests = [
    ("sort=oldest (no date filter)",
     {"q": KW, "limit": 25, "sort": "oldest"}),
    ("since=2023-01-01 until=2023-12-31",
     {"q": KW, "limit": 25, "since": "2023-01-01T00:00:00Z", "until": "2023-12-31T23:59:59Z"}),
    ("since=2024-01-01 until=2024-06-30",
     {"q": KW, "limit": 25, "since": "2024-01-01T00:00:00Z", "until": "2024-06-30T23:59:59Z"}),
    ("since=2025-01-01 until=2025-06-30",
     {"q": KW, "limit": 25, "since": "2025-01-01T00:00:00Z", "until": "2025-06-30T23:59:59Z"}),
]

for label, params in tests:
    print(f"\n[{label}]")
    try:
        resp = client.app.bsky.feed.search_posts(params=params)
        posts = resp.posts or []
        if not posts:
            print("  → 0 results")
            continue
        dates = sorted(p.record.created_at for p in posts if hasattr(p, "record"))
        print(f"  → {len(posts)} posts")
        print(f"     oldest: {dates[0]}")
        print(f"     newest: {dates[-1]}")
    except Exception as e:
        print(f"  → ERROR: {e}")
    time.sleep(1)
