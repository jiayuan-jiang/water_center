# Spec: Reddit Topics — Further Analysis

## Goal
Deepen the signal extracted from the existing 34-topic BERTopic model to support the Horizon Scan deliverable (late September 2026 workshop). No new data collection needed — all analyses draw from `data/topics/`.

---

## Input Files

| File | Description |
|------|-------------|
| `data/topics/documents_with_topics.csv` | 8,441 docs with topic ID, score, subreddit, created_utc, text |
| `data/topics/topic_summary.csv` | 34 topics with keyword representation |
| `data/topics/topics_over_time.html` | BERTopic-generated temporal visualization (needs narrative) |

---

## Analysis 1 — Temporal Trend Interpretation (HIGH PRIORITY)

**What:** Identify which topics are growing, declining, or newly emerging over 2023–2026.

**How:**
- Group `documents_with_topics.csv` by `(topic, month)`
- Compute normalized monthly document count per topic (control for total corpus volume)
- Flag topics where the slope of 2024–2026 vs 2023 is significantly positive → weak signal candidates
- Produce a ranked list: fastest-growing topics with example comments

**Output:** `data/analysis/topic_trends.csv` + narrative summary

**Why it matters:** Growing niche topics = core definition of a weak signal for Horizon Scan.

---

## Analysis 2 — Outlier Cluster (-1) Sub-clustering (HIGH PRIORITY)

> **Superseded by [spec/outlier-emerging-issues.md](outlier-emerging-issues.md)** — extends this
> analysis with relevance/novelty/recency scoring and a grounded candidate list.

**What:** Re-cluster the 3,717 documents currently labeled as noise (topic -1) to find hidden emerging topics too small for the original model.

**How:**
- Extract all `-1` documents from `documents_with_topics.csv`
- Re-run BERTopic on this subset with more permissive params:
  ```python
  HDBSCAN: min_cluster_size=10, min_samples=5  # lower than original (30, 10)
  ```
- Label any new clusters found; merge into a supplemental topic list

**Output:** `data/analysis/outlier_subclusters.csv`

**Why it matters:** The -1 bucket (44% of corpus) may contain the most novel weak signals — they're rare by definition.

---

## Analysis 3 — Sentiment Analysis per Topic (MEDIUM PRIORITY)

**What:** Classify each comment as positive / negative / neutral, then aggregate per topic.

**Model:** `cardiffnlp/twitter-roberta-base-sentiment` (fine-tuned on social media text)

**How:**
```python
from transformers import pipeline
pipe = pipeline("text-classification", model="cardiffnlp/twitter-roberta-base-sentiment")
# run on each row of documents_with_topics.csv['text']
# aggregate: mean sentiment score per topic
```

**Outputs:**
- `data/analysis/sentiment_by_topic.csv` — per-topic positive/negative/neutral %
- Controversy score = min(positive%, negative%) × 2 (high when both are high)

**Key questions:**
- Is "Offshore Wind Energy" (T15) seen as opportunity or threat?
- Is "Data Centers & Water" (T10) framed as alarm or curiosity?
- Which topics are most polarized (controversy score)?

---

## Analysis 4 — Subreddit × Topic Geographic Matrix (MEDIUM PRIORITY)

**What:** Use subreddit as a geographic proxy to map which topics are local vs. regional.

**How:**
- Cross-tabulate `subreddit` × `topic` from `documents_with_topics.csv`
- Normalize by subreddit size (row-normalize)
- Produce a heatmap: rows = subreddits, columns = topics, cell = % of that subreddit's docs in that topic

**Output:** `data/analysis/subreddit_topic_matrix.csv` + heatmap PNG

**Why it matters:** A topic concentrated in one state subreddit = local issue. A topic appearing across r/Michigan, r/ontario, r/ohio, r/wisconsin simultaneously = stronger regional weak signal.

---

## Analysis 5 — Engagement Analysis (MEDIUM PRIORITY)

**What:** Identify which topics generate highest community engagement via the `score` field.

**How:**
- Group by topic, compute: mean score, median score, top-10 highest-scored comments per topic
- Rank topics by mean score

**Output:** `data/analysis/topic_engagement.csv`

**Why it matters:** High-score topics = issues the community cares most about, not just niche discourse. Useful for prioritizing which topics to highlight in the report.

---

## Analysis 6 — Topic Semantic Similarity Network (LOW PRIORITY)

**What:** Build a topic-to-topic similarity matrix from BERTopic's internal embeddings to find clusters of related topics.

**How:**
- Extract centroid embeddings per topic from the fitted BERTopic model
- Compute cosine similarity matrix (34 × 34)
- Visualize as a network graph (edges above threshold ~0.5) or dendrogram

**Output:** `data/analysis/topic_similarity_network.html`

**Why it matters:** Helps the report group related topics (e.g., PFAS + Drinking Water Safety + Chemical Contamination are likely semantically close).

---

## Analysis 7 — STEEP Categorization (LOW PRIORITY, REPORT PREP)

**What:** Map each of the 34 topics to the standard Horizon Scan framework.

**Framework:**
| Category | Definition |
|----------|------------|
| S — Social | Public attitudes, community behavior, demographics |
| T — Technological | New technologies, innovation, data systems |
| E — Economic | Jobs, industry, markets, costs |
| E — Environmental | Ecosystems, climate, species, water quality |
| P — Political | Policy, regulation, governance, legal |

**How:** Manual classification (one or two STEEP tags per topic), output as a lookup table.

**Output:** `data/analysis/topic_steep.csv`

**Why it matters:** Standard deliverable format for Horizon Scan reports; helps structure the September workshop presentation.

---

## Suggested Execution Order

```
Week 1:  Analysis 1 (trends) + Analysis 2 (outlier sub-cluster)
Week 2:  Analysis 3 (sentiment) + Analysis 4 (geographic)
Week 3:  Analysis 5 (engagement) + Analysis 7 (STEEP tagging)
Pre-report: Analysis 6 (similarity network, optional)
```

---

## Notes

- All outputs go to `data/analysis/` (new directory, not in git)
- The BERTopic model object should be saved/loaded from `data/topics/` if available; otherwise re-fit from corpus
- Sentiment model requires `transformers` + `torch` — check conda env
