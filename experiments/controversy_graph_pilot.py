"""
Pilot: graph-based controversy (Random Walk Controversy, Garimella et al. 2018,
arXiv:1507.05224) on a handful of Reddit topics with concentrated thread
structure. See spec/controversy-score.md for why this is a pilot on 2-3
topics rather than the full pipeline — most topics' comments are scattered
across too many disconnected threads for a meaningful interaction graph.

Method:
1. For a topic, find the Reddit threads (link_id) its docs belong to
2. Pull ALL comments in those threads from data/comments_raw.jsonl (not just
   the topic-filtered subset) to reconstruct the real reply graph
3. Build an undirected author-interaction graph (edge = reply relationship)
4. 2-way partition the giant component (Kernighan-Lin bisection)
5. Estimate RWC via random-walk simulation: RWC = P_XX*P_YY - P_YX*P_XY
   (~1 = the two sides rarely talk to each other; ~0 = they freely mix)

Usage:
    python experiments/controversy_graph_pilot.py --topics 10,15,3
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import networkx as nx
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--topics", default="10,15,3", help="comma-separated Reddit topic IDs")
parser.add_argument("--walks", type=int, default=2000)
parser.add_argument("--walk-length", type=int, default=10)
args = parser.parse_args()

TOPIC_LABELS = {
    3: "Waterfront & Tourism", 10: "Data Centers & Water Consumption", 15: "Offshore Wind Energy",
}


def load_comment_index():
    idx = {}
    with open("data/comments_raw.jsonl") as f:
        for line in f:
            d = json.loads(line)
            idx[d["id"]] = {"author": d.get("author"), "parent_id": d.get("parent_id"), "link_id": d.get("link_id")}
    return idx


def load_post_authors():
    idx = {}
    with open("data/posts_raw.jsonl") as f:
        for line in f:
            d = json.loads(line)
            idx[d["id"]] = d.get("author")
    return idx


def build_thread_graph(link_ids, comments, post_authors):
    by_thread = defaultdict(list)
    for cid, c in comments.items():
        if c["link_id"] in link_ids:
            by_thread[c["link_id"]].append(cid)

    edges = defaultdict(int)
    bad_authors = {None, "[deleted]", "AutoModerator"}
    for link_id, cids in by_thread.items():
        for cid in cids:
            c = comments[cid]
            author = c["author"]
            if author in bad_authors:
                continue
            parent_id = c["parent_id"]
            if parent_id is None:
                continue
            if parent_id.startswith("t1_"):
                parent = comments.get(parent_id[3:])
                parent_author = parent["author"] if parent else None
            elif parent_id.startswith("t3_"):
                parent_author = post_authors.get(parent_id[3:])
            else:
                parent_author = None
            if parent_author in bad_authors or parent_author == author:
                continue
            key = tuple(sorted((author, parent_author)))
            edges[key] += 1

    G = nx.Graph()
    for (a, b), w in edges.items():
        G.add_edge(a, b, weight=w)
    return G


def estimate_rwc(G, side_x, side_y, n_walks, walk_length):
    def walk_end_side(start):
        node = start
        for _ in range(walk_length):
            neighbors = list(G.neighbors(node))
            if not neighbors:
                break
            weights = [G[node][nb]["weight"] for nb in neighbors]
            node = random.choices(neighbors, weights=weights, k=1)[0]
        return node

    def transition_probs(start_side, other_side):
        starts = random.choices(list(start_side), k=n_walks)
        end_in_start, end_in_other = 0, 0
        for s in starts:
            end = walk_end_side(s)
            if end in start_side:
                end_in_start += 1
            elif end in other_side:
                end_in_other += 1
        total = end_in_start + end_in_other
        return (end_in_start / total, end_in_other / total) if total else (0.0, 0.0)

    p_xx, p_xy = transition_probs(side_x, side_y)
    p_yy, p_yx = transition_probs(side_y, side_x)
    return p_xx * p_yy - p_yx * p_xy, {"P_XX": p_xx, "P_XY": p_xy, "P_YX": p_yx, "P_YY": p_yy}


def main():
    print("Loading raw comments + posts...")
    comments = load_comment_index()
    post_authors = load_post_authors()
    docs = pd.read_csv("data/topics/documents_with_topics.csv")

    for tid in [int(t) for t in args.topics.split(",")]:
        label = TOPIC_LABELS.get(tid, f"Topic {tid}")
        sub = docs[docs["topic"] == tid]
        link_ids = {comments[i]["link_id"] for i in sub["id"] if i in comments and comments[i]["link_id"]}
        print(f"\n=== Topic {tid} ({label}): {len(sub)} docs, {len(link_ids)} threads ===")

        G = build_thread_graph(link_ids, comments, post_authors)
        if G.number_of_nodes() < 10:
            print(f"  Graph too small ({G.number_of_nodes()} nodes) — skipping")
            continue

        components = sorted(nx.connected_components(G), key=len, reverse=True)
        giant = G.subgraph(components[0]).copy()
        giant_frac = len(components[0]) / G.number_of_nodes()
        print(f"  Full graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, "
              f"{len(components)} components")
        print(f"  Giant component: {giant.number_of_nodes()} nodes ({giant_frac:.0%} of graph), "
              f"{giant.number_of_edges()} edges")

        if giant.number_of_nodes() < 10:
            print("  Giant component too small for partitioning — skipping")
            continue

        side_x, side_y = nx.algorithms.community.kernighan_lin_bisection(giant, weight="weight", seed=42)
        print(f"  Partition: |X|={len(side_x)}, |Y|={len(side_y)}")

        rwc, probs = estimate_rwc(giant, side_x, side_y, args.walks, args.walk_length)
        print(f"  RWC = {rwc:.3f}  (P_XX={probs['P_XX']:.2f} P_XY={probs['P_XY']:.2f} "
              f"P_YX={probs['P_YX']:.2f} P_YY={probs['P_YY']:.2f})")


if __name__ == "__main__":
    main()
