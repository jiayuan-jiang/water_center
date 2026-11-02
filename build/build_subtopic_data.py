"""
Generate docs/data/subtopics/{reddit,bluesky}/t{N}.json and t{N}_s{M}.json
from grounded_summary.json + per-topic CSVs.
"""
import argparse
import csv
import json
import os
from datetime import datetime, timezone

PLATFORMS = {
    "reddit": {
        "summary":  "data/subtopics/grounded_summary.json",
        "csv_dir":  "data/subtopics",
        "corpus":   "data/corpus.jsonl",
        "out_dirs": ["docs/data/subtopics/reddit", "frontend/public/data/subtopics/reddit"],
        "id_col":   "id",
        "source_col": "subreddit",
    },
    "bluesky": {
        "summary":  "data/subtopics_bluesky/grounded_summary.json",
        "csv_dir":  "data/subtopics_bluesky",
        "corpus":   "data/corpus_bluesky.jsonl",
        "out_dirs": ["docs/data/subtopics/bluesky", "frontend/public/data/subtopics/bluesky"],
        "id_col":   "id",
        "source_col": "source",
    },
    "mastodon": {
        "summary":  "data/subtopics_mastodon/grounded_summary.json",
        "csv_dir":  "data/subtopics_mastodon",
        "corpus":   "data/corpus_mastodon.jsonl",
        "out_dirs": ["frontend/public/data/subtopics/mastodon"],
        "id_col":   "id",
        "source_col": "source",
    },
}


def load_bluesky_authors(corpus_path):
    authors = {}
    with open(corpus_path) as f:
        for line in f:
            row = json.loads(line)
            if "author" in row:
                authors[row["id"]] = row["author"]
    return authors


def load_emotion_by_doc(platform):
    """Per-comment emotion labels — same source build/build_docs_data.py joins in
    for main topic comments (data/analysis/sentiment_docs_{platform}.csv).
    Subtopic comment JSON was missing this field entirely."""
    path = f"data/analysis/sentiment_docs_{platform}.csv"
    if not os.path.exists(path):
        return {}
    emotion_by_doc = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            emotion_by_doc[row["id"]] = row["emotion"]
    return emotion_by_doc


def make_reddit_url(cid, post_id, subreddit):
    if post_id and cid:
        return f"https://www.reddit.com/r/{subreddit}/comments/{post_id}/_/{cid}/"
    return ""


def make_bluesky_url(cid, author):
    if author and cid:
        return f"https://bsky.app/profile/{author}/post/{cid}"
    return ""


def ts_to_date(ts):
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return ""


def build_platform(platform):
    cfg = PLATFORMS[platform]
    for d in cfg["out_dirs"]:
        os.makedirs(d, exist_ok=True)

    with open(cfg["summary"]) as f:
        summaries = json.load(f)

    bsky_authors = {}
    if platform == "bluesky":
        bsky_authors = load_bluesky_authors(cfg["corpus"])

    emotion_by_doc = load_emotion_by_doc(platform)

    for topic in summaries:
        tid = topic["topic_id"]
        csv_path = os.path.join(cfg["csv_dir"], f"topic_{tid:02d}.csv")
        if not os.path.exists(csv_path):
            print(f"  skip t{tid}: no CSV")
            continue

        # Group rows by subtopic
        groups: dict[int, list] = {}
        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                st = int(row["subtopic"])
                groups.setdefault(st, []).append(row)

        # Sort each group by score desc
        for st in groups:
            groups[st].sort(key=lambda r: int(r["score"]), reverse=True)

        # Build topic-level index
        subtopics_index = []
        for st_info in topic["subtopics"]:
            sid = st_info["subtopic_id"]
            gen = st_info.get("generated", {})
            rows = groups.get(sid, [])
            subtopics_index.append({
                "subtopic_id": sid,
                "doc_count":   st_info["doc_count"],
                "label":       gen.get("label", f"Sub-topic {sid}"),
                "attitude":    gen.get("attitude", ""),
                "summary":     gen.get("summary", ""),
                "key_quotes":  gen.get("key_quotes", []),
                "comment_ids": [r["id"] for r in rows],
            })

        t_index = {"topic_id": tid, "subtopics": subtopics_index}
        for out_dir in cfg["out_dirs"]:
            out_path = os.path.join(out_dir, f"t{tid}.json")
            with open(out_path, "w") as f:
                json.dump(t_index, f, ensure_ascii=False)

        # Build per-subtopic comment files
        for st_info in topic["subtopics"]:
            sid = st_info["subtopic_id"]
            rows = groups.get(sid, [])
            comments = []
            for r in rows:
                cid = r["id"]
                if platform == "reddit":
                    url = make_reddit_url(cid, r.get("post_id", ""), r.get("subreddit", ""))
                    source = r.get("subreddit", "")
                elif platform == "mastodon":
                    url = r.get("url", "")
                    source = r.get("author", "")
                else:
                    url = make_bluesky_url(cid, bsky_authors.get(cid, ""))
                    source = "bluesky"
                comments.append({
                    "id":      cid,
                    "source":  source,
                    "score":   int(r["score"]),
                    "date":    ts_to_date(r["created_utc"]),
                    "text":    r["text"],
                    "url":     url,
                    "emotion": emotion_by_doc.get(cid),
                })
            gen = st_info.get("generated", {})
            out = {
                "topic_id":    tid,
                "subtopic_id": sid,
                "label":       gen.get("label", f"Sub-topic {sid}"),
                "comments":    comments,
            }
            for out_dir in cfg["out_dirs"]:
                s_path = os.path.join(out_dir, f"t{tid}_s{sid}.json")
                with open(s_path, "w") as f:
                    json.dump(out, f, ensure_ascii=False)

        print(f"  t{tid}: {len(subtopics_index)} subtopics, {sum(len(g) for g in groups.values())} docs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon", "all"], default="all")
    args = parser.parse_args()

    targets = ["reddit", "bluesky", "mastodon"] if args.platform == "all" else [args.platform]
    for p in targets:
        print(f"\n=== {p} ===")
        build_platform(p)


if __name__ == "__main__":
    main()
