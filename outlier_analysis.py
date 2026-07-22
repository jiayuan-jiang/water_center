"""
Outlier micro-clustering + emerging-issue scoring.
Spec: spec/outlier-emerging-issues.md

Input:  data/topics{,_bluesky}/documents_with_topics.csv (topic == -1 subset)
Output: data/analysis/outlier_subclusters_{platform}.csv   all clusters + scores
        data/analysis/outlier_overview_{platform}.json     relevance-passing clusters
        data/analysis/outlier_docs_{platform}.csv          per-doc cluster assignments
        data/analysis/outlier_review_{platform}.md         human review sheet

Embeddings are cached in data/analysis/.emb_cache_{platform}.npz — reruns with
different clustering/scoring params skip the encoding step (~seconds instead of
minutes). Cache invalidates automatically when the input doc set changes.

Usage:
    python outlier_analysis.py --platform reddit
    python outlier_analysis.py --platform bluesky --min-relevance 0.35
    python outlier_analysis.py --platform reddit --min-cluster-size 8 \\
        --recency-months 18 --novelty-weight 2.0
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from umap import UMAP
from hdbscan import HDBSCAN

# keep in sync with topic_model.SEED_TOPICS (importing it would run the pipeline)
SEED_TOPICS = [
    ["water quality", "pollution", "contamination", "PFAS", "chemicals", "toxic"],
    ["invasive species", "carp", "sea lamprey", "zebra mussel", "Asian carp"],
    ["algal bloom", "algae", "cyanobacteria", "phosphorus", "nutrients", "HAB"],
    ["water level", "lake level", "flooding", "drought", "water shortage"],
    ["climate change", "temperature", "ice cover", "warming", "precipitation"],
    ["fishing", "fishery", "fish population", "sport fishing", "anglers"],
    ["drinking water", "water treatment", "infrastructure", "lead pipes"],
    ["recreation", "swimming", "beach", "boating", "tourism"],
    ["conservation", "wildlife", "habitat", "wetland", "biodiversity"],
    ["policy", "regulation", "EPA", "government", "funding", "legislation"],
]

BLUESKY_BOT_AUTHORS = {
    "mqt.weather.im", "mqt.nws-bot.us", "onwxalerts.bsky.social",
    "wpc.weather.im", "grr.nws-bot.us", "chi.nws-bot.us", "dlh.nws-bot.us",
    "skeetbot.watchedsky.social", "amtrak-status.paxex.aero",
    "weather-alerts-ca.bsky.social", "advanceweather.bsky.social",
    "cle.nws-bot.us", "iwx.nws-bot.us",
    # formulaic/automated accounts found in outlier micro-clusters (2026-07-22)
    "glicetracker.bsky.social", "wjonip.org", "zerodata.bsky.social",
    "mwrdgc.bsky.social", "bigearthdata.ai",
}

# any handle on these bot domains, or containing "bot", is automated
BLUESKY_BOT_AUTHOR_RE = r"(\.nws-bot\.us$|\.weather\.im$|bot)"

# "Great Lakes" also names the African Great Lakes region — drop that discourse
AFRICA_TERMS_RE = (r"\b(africa|african|uganda|kenya|tanzania|rwanda|burundi|"
                   r"congo|malawi|zambia|nile|lake victoria|tanganyika|kivu)\b")


def parse_args():
    p = argparse.ArgumentParser(
        description="Outlier micro-clustering + relevance/novelty/recency scoring",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--platform", choices=["reddit", "bluesky"], default="reddit")

    g = p.add_argument_group("clustering")
    g.add_argument("--min-cluster-size", type=int, default=10,
                   help="HDBSCAN min_cluster_size (main model uses 30)")
    g.add_argument("--min-samples", type=int, default=5,
                   help="HDBSCAN min_samples (main model uses 10)")
    g.add_argument("--umap-neighbors", type=int, default=15,
                   help="UMAP n_neighbors; lower = finer local structure")
    g.add_argument("--umap-components", type=int, default=5)

    g = p.add_argument_group("scoring")
    g.add_argument("--min-relevance", type=float, default=0.3,
                   help="hard gate: drop clusters below this cos-sim to seed anchor")
    g.add_argument("--recency-months", type=int, default=12,
                   help="window (from corpus end) counted as 'recent'")
    g.add_argument("--novelty-weight", type=float, default=1.0,
                   help="rank_score = novelty^w_n * recency^w_r")
    g.add_argument("--recency-weight", type=float, default=1.0)

    g = p.add_argument_group("output")
    g.add_argument("--n-repr-docs", type=int, default=3,
                   help="representative docs per cluster in overview/review")
    g.add_argument("--n-keywords", type=int, default=10)
    g.add_argument("--no-cache", action="store_true",
                   help="ignore embedding cache and re-encode")
    return p.parse_args()


def normed(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def load_or_encode(model, cache_path: Path, ids: pd.Series, texts: list[str],
                   use_cache: bool) -> np.ndarray:
    ids_arr = ids.astype(str).to_numpy(dtype="U")
    if use_cache and cache_path.exists():
        cached = np.load(cache_path, allow_pickle=False)
        if len(cached["ids"]) == len(ids_arr) and bool((cached["ids"] == ids_arr).all()):
            print(f"  cache hit: {cache_path.name}")
            return cached["emb"]
    emb = normed(model.encode(texts, show_progress_bar=True, batch_size=64))
    np.savez_compressed(cache_path, ids=ids_arr, emb=emb)
    return emb


def cluster_keywords(tfidf_mat, vocab, mask, n):
    mean_tfidf = np.asarray(tfidf_mat[mask].mean(axis=0)).ravel()
    return vocab[np.argsort(mean_tfidf)[::-1][:n]].tolist()


def write_review_md(path: Path, meta: dict, clusters: list[dict],
                    rejected: pd.DataFrame):
    lines = [
        f"# [REVIEW DRAFT] {meta['platform']} outlier micro-clusters — 人工审阅",
        "",
        f"输入 {meta['n_outlier_docs']:,} 条 outlier 文档 → {meta['n_clusters']} 个微簇，"
        f"{meta['n_passing']} 个通过 relevance ≥ {meta['params']['min_relevance']}，"
        f"残余噪声 {meta['residual_noise']:,} 条。",
        f"参数: `{json.dumps(meta['params'])}`",
        "",
        "按 rank_score 排序。审阅标注：**E**(emerging 候选) / **K**(已知话题碎片) / **N**(噪声)。",
        "",
        "---",
    ]
    for rank, c in enumerate(clusters, 1):
        trend = " ".join(f"{m}:{n}" for m, n in c["monthly_counts"].items())
        lines += [
            "",
            f"## {rank}. 簇 {c['cluster_id']} — {', '.join(c['keywords'][:5])}",
            "",
            f"- 文档数 {c['n_docs']} | relevance {c['relevance']} | "
            f"novelty {c['novelty']} | recency {c['recency']:.0%} | "
            f"rank_score {c['rank_score']}",
            f"- 活跃期 {c['first_month']} → {c['last_month']}",
            f"- 月度分布: {trend}",
            f"- 关键词: {', '.join(c['keywords'])}",
            "- 审阅标注: [ ]",
            "",
            "代表评论:",
        ]
        for d in c["repr_docs"]:
            text = d["text"].replace("\n", " ")
            if len(text) > 400:
                text = text[:400] + "…"
            lines.append(f"> [{d['id']}] (score={d['score']}) {text}")
            lines.append(">")
        lines.append("---")

    lines += ["", "## 附录：被 relevance 门槛剔除的簇（核对是否误杀）", "",
              "| 簇 | 文档数 | relevance | 关键词 |",
              "|----|--------|-----------|--------|"]
    for _, r in rejected.sort_values("relevance", ascending=False).iterrows():
        lines.append(f"| {r['cluster']} | {r['n_docs']} | {r['relevance']} | {r['keywords']} |")
    path.write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    params = {
        "min_cluster_size": args.min_cluster_size,
        "min_samples": args.min_samples,
        "umap_neighbors": args.umap_neighbors,
        "umap_components": args.umap_components,
        "min_relevance": args.min_relevance,
        "recency_months": args.recency_months,
        "novelty_weight": args.novelty_weight,
        "recency_weight": args.recency_weight,
    }

    docs_csv = Path("data/topics/documents_with_topics.csv" if args.platform == "reddit"
                    else "data/topics_bluesky/documents_with_topics.csv")
    out_dir = Path("data/analysis")
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_out = out_dir / f"outlier_subclusters_{args.platform}.csv"
    json_out = out_dir / f"outlier_overview_{args.platform}.json"
    docs_out = out_dir / f"outlier_docs_{args.platform}.csv"
    review_out = out_dir / f"outlier_review_{args.platform}.md"

    df = pd.read_csv(docs_csv)
    df["created_dt"] = pd.to_datetime(df["created_dt"])
    df["month"] = df["created_dt"].dt.strftime("%Y-%m")

    outliers = df[df["topic"] == -1].copy()
    if args.platform == "bluesky":
        n0 = len(outliers)
        outliers = outliers[~outliers["author"].isin(BLUESKY_BOT_AUTHORS)]
        outliers = outliers[~outliers["author"].str.contains(
            BLUESKY_BOT_AUTHOR_RE, regex=True, na=False)]
        n1 = len(outliers)
        outliers = outliers[~outliers["text"].str.contains(
            AFRICA_TERMS_RE, case=False, regex=True, na=False)]
        n2 = len(outliers)
        norm = (outliers["text"].str.lower()
                .str.replace(r"http\S+", "", regex=True)
                .str.replace(r"[^a-z0-9 ]", "", regex=True)
                .str.replace(r"\s+", " ", regex=True).str.strip())
        dup = norm.duplicated() | (outliers["author"] + "|" + norm.str[:60]).duplicated()
        outliers = outliers[~dup]
        print(f"Filters: {n0:,} → bots {n1:,} → africa {n2:,} "
              f"→ dedup {len(outliers):,} outlier docs")
    outliers = outliers.reset_index(drop=True)
    print(f"Corpus: {len(df):,} docs, outliers to analyze: {len(outliers):,}")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    print("Embedding outlier docs...")
    out_emb = load_or_encode(model,
                             out_dir / f".emb_cache_outliers_{args.platform}.npz",
                             outliers["id"], outliers["text"].tolist(),
                             not args.no_cache)

    print("Embedding assigned docs for topic centroids...")
    assigned = df[df["topic"] != -1]
    asg_emb = load_or_encode(model,
                             out_dir / f".emb_cache_assigned_{args.platform}.npz",
                             assigned["id"], assigned["text"].tolist(),
                             not args.no_cache)
    topic_centroids = normed(np.stack([
        asg_emb[(assigned["topic"] == t).to_numpy()].mean(axis=0)
        for t in sorted(assigned["topic"].unique())
    ]))

    anchor = normed(normed(
        model.encode([" ".join(s) for s in SEED_TOPICS])).mean(axis=0))

    print("UMAP + HDBSCAN...")
    reduced = UMAP(n_neighbors=args.umap_neighbors,
                   n_components=args.umap_components,
                   min_dist=0.0, metric="cosine",
                   random_state=42).fit_transform(out_emb)
    labels = HDBSCAN(min_cluster_size=args.min_cluster_size,
                     min_samples=args.min_samples,
                     metric="euclidean",
                     cluster_selection_method="eom").fit_predict(reduced)

    cluster_ids = sorted(int(c) for c in set(labels) if c != -1)
    residual = int((labels == -1).sum())
    print(f"Micro-clusters: {len(cluster_ids)}, residual noise: "
          f"{residual:,}/{len(outliers):,} ({residual/len(outliers):.0%})")

    tfidf = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", min_df=3)
    tfidf_mat = tfidf.fit_transform(outliers["text"])
    vocab = np.array(tfidf.get_feature_names_out())

    recency_cut = df["created_dt"].max() - pd.DateOffset(months=args.recency_months)

    rows, overview = [], []
    for cid in cluster_ids:
        mask = (labels == cid)
        sub = outliers[mask]
        centroid = normed(out_emb[mask].mean(axis=0))

        relevance = float(centroid @ anchor)
        novelty = float(1 - (topic_centroids @ centroid).max())
        recency = float((sub["created_dt"] >= recency_cut).mean())
        rank_score = (novelty ** args.novelty_weight) * (recency ** args.recency_weight)
        monthly = sub["month"].value_counts().sort_index()
        keywords = cluster_keywords(tfidf_mat, vocab, mask, args.n_keywords)

        row = {
            "cluster": cid,
            "n_docs": len(sub),
            "relevance": round(relevance, 3),
            "novelty": round(novelty, 3),
            "recency": round(recency, 3),
            "rank_score": round(rank_score, 3),
            "first_month": monthly.index[0],
            "last_month": monthly.index[-1],
            "keywords": ", ".join(keywords),
            "passes_relevance": relevance >= args.min_relevance,
        }
        rows.append(row)

        if not row["passes_relevance"]:
            continue
        sims = out_emb[mask] @ centroid
        repr_idx = sub.index[np.argsort(sims)[::-1][:args.n_repr_docs]]
        overview.append({
            "cluster_id": cid,
            "n_docs": len(sub),
            "relevance": row["relevance"],
            "novelty": row["novelty"],
            "recency": row["recency"],
            "rank_score": row["rank_score"],
            "first_month": row["first_month"],
            "last_month": row["last_month"],
            "keywords": keywords,
            "monthly_counts": {k: int(v) for k, v in monthly.items()},
            "repr_docs": [
                {"id": str(outliers.loc[i, "id"]),
                 "score": int(outliers.loc[i, "score"]),
                 "text": str(outliers.loc[i, "text"])[:1000]}
                for i in repr_idx
            ],
        })

    summary = pd.DataFrame(rows).sort_values("rank_score", ascending=False)
    summary.to_csv(csv_out, index=False)
    overview.sort(key=lambda c: c["rank_score"], reverse=True)

    source_col = "subreddit" if "subreddit" in outliers.columns else "source"
    outliers["cluster"] = labels
    passing_ids = {c["cluster_id"] for c in overview}
    doc_cols = ["id", "cluster", source_col, "author", "score", "created_dt", "text"]
    outliers[outliers["cluster"].isin(passing_ids)][doc_cols].to_csv(docs_out, index=False)

    meta = {
        "platform": args.platform,
        "params": params,
        "n_outlier_docs": len(outliers),
        "n_clusters": len(cluster_ids),
        "n_passing": len(overview),
        "residual_noise": residual,
    }
    json_out.write_text(json.dumps({**meta, "clusters": overview},
                                   ensure_ascii=False, indent=2))
    write_review_md(review_out, meta, overview, summary[~summary["passes_relevance"]])

    passing = summary[summary["passes_relevance"]]
    print(f"\nRelevance gate (>= {args.min_relevance}): "
          f"{len(passing)}/{len(cluster_ids)} clusters pass")
    print(f"\nTop 15 candidates by rank_score:")
    print(passing.head(15)[["cluster", "n_docs", "relevance", "novelty",
                            "recency", "rank_score", "first_month", "keywords"]]
          .to_string(index=False, max_colwidth=60))
    print(f"\nWritten: {csv_out}\n         {json_out}\n         {docs_out}\n         {review_out}")


if __name__ == "__main__":
    main()
