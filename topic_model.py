"""
Guided BERTopic analysis on cleaned Great Lakes Reddit corpus.
Input:  data/corpus.jsonl
Output: data/topics/  (topic table, representative docs, visualizations)
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

from sentence_transformers import SentenceTransformer
from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer

# ── Paths ────────────────────────────────────────────────────────────────────
CORPUS_FILE = Path("data/corpus.jsonl")
OUT_DIR     = Path("data/topics")
OUT_DIR.mkdir(exist_ok=True)

# ── Seed topics (Guided BERTopic) ────────────────────────────────────────────
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

# ── Load corpus ───────────────────────────────────────────────────────────────
records = [json.loads(l) for l in CORPUS_FILE.open()]
docs     = [r["text"] for r in records]
df       = pd.DataFrame(records)
df["created_dt"] = pd.to_datetime(df["created_utc"], unit="s")

print(f"Corpus: {len(docs):,} documents")
print(f"Date range: {df['created_dt'].min().date()} → {df['created_dt'].max().date()}")

# ── Embedding model ───────────────────────────────────────────────────────────
print("\nLoading embedding model...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

print("Encoding documents...")
embeddings = embedding_model.encode(docs, show_progress_bar=True, batch_size=64)

# ── BERTopic components ───────────────────────────────────────────────────────
umap_model = UMAP(
    n_neighbors=15,
    n_components=5,
    min_dist=0.0,
    metric="cosine",
    random_state=42,
)

hdbscan_model = HDBSCAN(
    min_cluster_size=30,
    min_samples=10,
    metric="euclidean",
    cluster_selection_method="eom",
    prediction_data=True,
)

vectorizer = CountVectorizer(
    ngram_range=(1, 2),
    stop_words="english",
    min_df=5,
)

representation_model = KeyBERTInspired()

# ── Build model ───────────────────────────────────────────────────────────────
topic_model = BERTopic(
    embedding_model=embedding_model,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer,
    representation_model=representation_model,
    seed_topic_list=SEED_TOPICS,
    nr_topics="auto",
    verbose=True,
)

print("\nFitting BERTopic...")
topics, probs = topic_model.fit_transform(docs, embeddings)

# ── Results ───────────────────────────────────────────────────────────────────
topic_info = topic_model.get_topic_info()
print(f"\nTopics found: {len(topic_info) - 1} (excluding outliers)")
print(topic_info[topic_info["Topic"] != -1][["Topic", "Count", "Name"]].to_string(index=False))

# save topic summary
topic_info.to_csv(OUT_DIR / "topic_summary.csv", index=False)

# save documents with assigned topics
df["topic"] = topics
df["topic_prob"] = probs if hasattr(probs, "__iter__") else [probs] * len(docs)
df.to_csv(OUT_DIR / "documents_with_topics.csv", index=False)

# save representative docs per topic
with open(OUT_DIR / "representative_docs.txt", "w") as f:
    for tid in sorted(topic_info["Topic"].unique()):
        if tid == -1:
            continue
        info = topic_info[topic_info["Topic"] == tid].iloc[0]
        f.write(f"\n{'='*60}\n")
        f.write(f"Topic {tid}: {info['Name']}\n")
        f.write(f"Count: {info['Count']} documents\n")
        f.write(f"Keywords: {topic_model.get_topic(tid)[:8]}\n")
        f.write("Representative docs:\n")
        rep_docs = topic_model.get_representative_docs(tid)
        if isinstance(rep_docs, dict):
            rep_docs = rep_docs.get(tid, [])
        for doc in rep_docs[:3]:
            f.write(f"  - {doc[:300]}\n")

# ── Visualizations ────────────────────────────────────────────────────────────
print("\nGenerating visualizations...")

fig_bar = topic_model.visualize_barchart(top_n_topics=20, n_words=8)
fig_bar.write_html(OUT_DIR / "topics_barchart.html")

fig_topics = topic_model.visualize_topics()
fig_topics.write_html(OUT_DIR / "topics_map.html")

# Topics over time
timestamps = df["created_dt"].tolist()
topics_over_time = topic_model.topics_over_time(docs, timestamps, nr_bins=20)
fig_time = topic_model.visualize_topics_over_time(topics_over_time, top_n_topics=10)
fig_time.write_html(OUT_DIR / "topics_over_time.html")

print(f"\nDone. Results saved to {OUT_DIR.resolve()}/")
print(f"  - topic_summary.csv")
print(f"  - documents_with_topics.csv")
print(f"  - representative_docs.txt")
print(f"  - topics_barchart.html")
print(f"  - topics_map.html")
print(f"  - topics_over_time.html")
