"""
Topic-to-topic semantic similarity network.

Builds a node/edge graph per (platform, node-set) by re-embedding each
topic/cluster's actual assigned documents with the same model used for
BERTopic (all-MiniLM-L6-v2), mean-pooling into a centroid vector, then
computing pairwise cosine similarity. Edges are kept above --threshold
(hard cutoff — no node filtering, per spec/reddit-further-analysis.md
Analysis 6, extended to outlier micro-clusters and both platforms).

Node sets:
  topics   -> frontend/public/data/{,bluesky/}topics.json (labeled topics)
  outliers -> frontend/public/data/outliers/{platform}/clusters.json (passing micro-clusters)

Usage:
    python topic_similarity_network.py --platform reddit --set topics
    python topic_similarity_network.py --platform bluesky --set outliers
    python topic_similarity_network.py --all   # runs all 4 combos
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

SAMPLE_PER_NODE = 80
SEED = 42

TOPICS_JSON = {
    "reddit": Path("frontend/public/data/topics.json"),
    "bluesky": Path("frontend/public/data/bluesky/topics.json"),
    "mastodon": Path("frontend/public/data/mastodon/topics.json"),
}
DOCS_WITH_TOPICS = {
    "reddit": Path("data/topics/documents_with_topics.csv"),
    "bluesky": Path("data/topics_bluesky/documents_with_topics.csv"),
    "mastodon": Path("data/topics_mastodon/documents_with_topics.csv"),
}
OUTLIER_CLUSTERS_JSON = {
    "reddit": Path("frontend/public/data/outliers/reddit/clusters.json"),
    "bluesky": Path("frontend/public/data/outliers/bluesky/clusters.json"),
    "mastodon": Path("frontend/public/data/outliers/mastodon/clusters.json"),
}
OUTLIER_DOCS_CSV = {
    "reddit": Path("data/analysis/outlier_docs_reddit.csv"),
    "bluesky": Path("data/analysis/outlier_docs_bluesky.csv"),
    "mastodon": Path("data/analysis/outlier_docs_mastodon.csv"),
}
OUT_DIR = Path("frontend/public/data/network")


def load_topic_nodes(platform):
    meta = json.loads(TOPICS_JSON[platform].read_text())
    nodes = [{"id": t["id"], "label": t["label"], "keywords": t["keywords"], "count": t["count"],
              "controversy": t.get("controversy"), "emotion": t.get("emotion")}
              for t in meta["topics"]]
    docs = pd.read_csv(DOCS_WITH_TOPICS[platform])
    node_ids = {n["id"] for n in nodes}
    docs = docs[docs["topic"].isin(node_ids)]
    texts_by_node = {tid: g["text"].tolist() for tid, g in docs.groupby("topic")}
    return nodes, texts_by_node


def load_outlier_nodes(platform):
    meta = json.loads(OUTLIER_CLUSTERS_JSON[platform].read_text())
    # No LLM controversy score exists for outlier clusters (only run on labeled
    # topics) — emotion is available since outlier_emotion.py covers all clusters.
    nodes = [{"id": c["id"], "label": c["label"], "keywords": c["keywords"], "count": c["n_docs"],
              "emotion": c.get("emotion")}
              for c in meta["clusters"]]
    docs = pd.read_csv(OUTLIER_DOCS_CSV[platform])
    node_ids = {n["id"] for n in nodes}
    docs = docs[docs["cluster"].isin(node_ids)]
    texts_by_node = {cid: g["text"].tolist() for cid, g in docs.groupby("cluster")}
    return nodes, texts_by_node


LOADERS = {"topics": load_topic_nodes, "outliers": load_outlier_nodes}


def build_centroids(nodes, texts_by_node, model):
    rng = np.random.default_rng(SEED)
    flat_texts, owners = [], []
    for n in nodes:
        texts = texts_by_node.get(n["id"], [])
        if len(texts) > SAMPLE_PER_NODE:
            idx = rng.choice(len(texts), SAMPLE_PER_NODE, replace=False)
            texts = [texts[i] for i in idx]
        flat_texts.extend(texts)
        owners.extend([n["id"]] * len(texts))

    print(f"  Embedding {len(flat_texts)} sampled docs across {len(nodes)} nodes...")
    embeddings = model.encode(flat_texts, batch_size=64, show_progress_bar=True)

    owners = np.array(owners)
    centroids = {}
    for n in nodes:
        mask = owners == n["id"]
        if mask.sum() == 0:
            centroids[n["id"]] = None
            continue
        vec = embeddings[mask].mean(axis=0)
        centroids[n["id"]] = vec / np.linalg.norm(vec)
    return centroids


def build_graph(platform, node_set, threshold, model):
    print(f"\n=== {platform} / {node_set} ===")
    nodes, texts_by_node = LOADERS[node_set](platform)
    centroids = build_centroids(nodes, texts_by_node, model)
    nodes = [n for n in nodes if centroids[n["id"]] is not None]

    ids = [n["id"] for n in nodes]
    matrix = np.stack([centroids[i] for i in ids])
    sim = matrix @ matrix.T

    edges = []
    for a in range(len(ids)):
        for b in range(a + 1, len(ids)):
            w = float(sim[a, b])
            if w >= threshold:
                edges.append({"source": ids[a], "target": ids[b], "weight": round(w, 4)})

    print(f"  {len(nodes)} nodes, {len(edges)} edges >= {threshold}")

    out = {
        "platform": platform,
        "set": node_set,
        "threshold": threshold,
        "embedding_model": "all-MiniLM-L6-v2",
        "generated": pd.Timestamp.now("UTC").strftime("%Y-%m-%d"),
        "nodes": [{**n, "keywords": n["keywords"][:6]} for n in nodes],
        "edges": edges,
    }
    out_path = OUT_DIR / platform / f"{node_set}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2))
    print(f"  -> {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=["reddit", "bluesky", "mastodon"])
    parser.add_argument("--set", dest="node_set", choices=["topics", "outliers"])
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--all", action="store_true", help="run all platform x set combos")
    args = parser.parse_args()

    print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    if args.all:
        for platform in ("reddit", "bluesky", "mastodon"):
            for node_set in ("topics", "outliers"):
                build_graph(platform, node_set, args.threshold, model)
    else:
        if not args.platform or not args.node_set:
            parser.error("either --all, or both --platform and --set")
        build_graph(args.platform, args.node_set, args.threshold, model)


if __name__ == "__main__":
    main()
