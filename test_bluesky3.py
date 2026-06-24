"""
Inspect raw structure of a Bluesky searchPosts result.
"""

import os, json
from atproto import Client

client = Client()
client.login(os.environ["BSKY_USER"], os.environ["BSKY_PASS"])

resp = client.app.bsky.feed.search_posts(
    params={"q": "Great Lakes", "limit": 2,
            "since": "2024-01-01T00:00:00Z", "until": "2024-01-31T23:59:59Z"}
)

post = resp.posts[0]

print("=== Top-level keys on a post object ===")
print([k for k in dir(post) if not k.startswith("_")])

print("\n=== post.record (the actual content) ===")
r = post.record
print(f"  created_at : {r.created_at}")
print(f"  text       : {r.text[:200]!r}")
print(f"  langs      : {getattr(r, 'langs', None)}")
print(f"  reply      : {getattr(r, 'reply', None)}")  # present if this is a reply

print("\n=== post metadata ===")
print(f"  uri        : {post.uri}")      # unique ID (at://did/.../rkey)
print(f"  cid        : {post.cid}")
print(f"  author.handle : {post.author.handle}")
print(f"  author.did    : {post.author.did}")
print(f"  like_count    : {post.like_count}")
print(f"  reply_count   : {post.reply_count}")
print(f"  repost_count  : {post.repost_count}")

print("\n=== reply field (is this post a reply?) ===")
reply = getattr(r, "reply", None)
if reply:
    print(f"  parent.uri : {reply.parent.uri}")
    print(f"  root.uri   : {reply.root.uri}")
else:
    print("  (this post is NOT a reply — it's a root post)")

print("\n=== Second post ===")
post2 = resp.posts[1]
r2 = post2.record
reply2 = getattr(r2, "reply", None)
print(f"  text   : {r2.text[:120]!r}")
print(f"  reply? : {'YES → parent=' + reply2.parent.uri if reply2 else 'NO (root post)'}")
