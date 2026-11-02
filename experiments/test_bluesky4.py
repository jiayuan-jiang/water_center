"""
Test: keyword matching behavior on Bluesky searchPosts.
- Exact phrase vs individual words
- Hashtag search
- Case sensitivity
"""

import os, time
from atproto import Client

client = Client()
client.login(os.environ["BSKY_USER"], os.environ["BSKY_PASS"])

WINDOW = {"since": "2024-01-01T00:00:00Z", "until": "2024-12-31T23:59:59Z"}

tests = [
    ('exact phrase "Great Lakes"',      "Great Lakes"),
    ('lowercase "great lakes"',         "great lakes"),
    ('single word "greatlakes"',        "greatlakes"),
    ('hashtag #GreatLakes',             "#GreatLakes"),
    ('hashtag #greatlakes',             "#greatlakes"),
    ('"Lake Michigan" OR "Lake Erie"',  "Lake Michigan OR Lake Erie"),
]

for label, q in tests:
    try:
        resp = client.app.bsky.feed.search_posts(
            params={"q": q, "limit": 5, **WINDOW}
        )
        posts = resp.posts or []
        print(f"\n[{label}]  → {len(posts)} results")
        for p in posts[:2]:
            print(f"   {p.record.text[:100]!r}")
    except Exception as e:
        print(f"\n[{label}]  → ERROR: {e}")
    time.sleep(0.5)
