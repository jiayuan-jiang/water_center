# Spec: Outlier → Emerging Issues Extraction

## Goal
Turn the BERTopic outlier bucket (topic -1) into a reviewable list of emerging-issue
candidates for the Horizon Scan master list, in the same format as the literature-review
list (issue title + short description + source).

Reddit: 3,717 outlier docs (44%). Bluesky: 53,826 (43%).

## Definition mapping

An emerging issue (per 0629 meeting, Ian's criteria) receives little/no attention, is
poorly understood, has no clear solutions or governance, impacts the basin within 10–20
years, or exists now but will grow greatly in magnitude. Hard constraint: water-related,
Great Lakes basin.

Outlier ≠ emerging. The -1 bucket mixes (a) off-topic noise, (b) generic chatter, and
(c) real signals too rare to form a cluster of ≥30 docs. Only (c) matters. The meeting
definition is operationalized as three computable filters on micro-clusters:

| Meeting criterion | Corpus proxy |
|---|---|
| Low attention | Small cluster (10–30 docs, below main-model threshold) |
| Water / Great Lakes related | `relevance`: cosine sim of cluster centroid to seed-keyword anchor |
| Genuinely new, not a fragment of a known topic | `novelty`: 1 − max cosine sim to existing topic centroids |
| Growing / recently appeared | `recency`: share of docs in the last 12 months + first-seen month |

Bias toward recall: Manja/Ian committed to triaging a long list manually
("not emerging / relevant / don't know"), so keep every cluster that passes the
relevance gate and let novelty × recency drive the ordering, not exclusion.

## Method

### Tunable parameters (`analysis/outlier_analysis.py` CLI)

| Flag | Default | Controls |
|------|---------|----------|
| `--min-cluster-size` / `--min-samples` | 10 / 5 | HDBSCAN granularity (main model: 30/10) |
| `--umap-neighbors` / `--umap-components` | 15 / 5 | UMAP; lower neighbors = finer local structure |
| `--min-relevance` | 0.3 | hard gate vs. seed-keyword anchor |
| `--recency-months` | 12 | window counted as "recent" |
| `--novelty-weight` / `--recency-weight` | 1.0 / 1.0 | `rank_score = novelty^wn × recency^wr` |
| `--n-repr-docs` / `--n-keywords` | 3 / 10 | output verbosity |
| `--no-cache` | off | force re-encoding |

All params are recorded in the output JSON (`params` key) for reproducibility.
Embeddings are cached (`data/analysis/.emb_cache_*.npz`, auto-invalidated when the
input doc set changes), so param sweeps rerun in seconds. The human review sheet
`data/analysis/outlier_review_{platform}.md` is regenerated on every run.

### Stage 1 — micro-clustering (`analysis/outlier_analysis.py`)
- Input: `data/topics{,_bluesky}/documents_with_topics.csv`, rows with `topic == -1`
- Bluesky only: drop docs from known weather/status bot authors (blocklist from
  task-queue) before clustering — input filter only, main pipeline untouched
- Re-embed with `all-MiniLM-L6-v2` (main model was not saved; re-encoding is cheap)
- UMAP: same params as `analysis/topic_model.py` (n_neighbors=15, n_components=5, min_dist=0.0,
  cosine, random_state=42)
- HDBSCAN: `min_cluster_size=10, min_samples=5` (main model: 30, 10)

### Stage 2 — scoring per micro-cluster
- `relevance` = cos(cluster centroid, anchor), anchor = mean embedding of the
  SEED_TOPICS keyword phrases from `analysis/topic_model.py`. Clusters below
  `--min-relevance` (default 0.3, tune after first run) are dropped as off-topic.
- `novelty` = 1 − max cos(cluster centroid, existing topic centroids). Topic centroids
  are mean embeddings of non-outlier docs grouped by assigned topic. Low novelty is
  down-weighted, not dropped (may be a new facet of a known topic).
- `recency` = share of cluster docs in the final 12 months of the corpus; also record
  first-seen month and full monthly counts for trend plotting.
- Ranking score = `novelty × recency` among relevance-passing clusters.
- Centroids and similarities computed in original embedding space (not UMAP space).

Outputs:
- `data/analysis/outlier_subclusters_{platform}.csv` — all clusters with scores
- `data/analysis/outlier_overview_{platform}.json` — relevance-passing clusters with
  keywords (per-cluster mean TF-IDF top terms), scores, monthly counts, and top-3
  representative docs (closest to centroid)

### Stage 3 — grounded candidate list (`llm/outlier_candidates.py`)
- For each cluster in the overview JSON, call Gemini 2.5 Flash (same pattern as
  `llm/grounded_summary.py`: checkpointed, cited to doc IDs) to produce an issue title +
  2–3 sentence description + key quotes.
- Output `data/analysis/emerging_issues_candidates_{platform}.md`: table with
  issue / description / source / n_docs / date range / novelty / example quotes —
  the reviewable deliverable for Manja & Ian.

## Execution order
1. Reddit pilot (3,717 docs) → manual sanity review, tune `--min-relevance`
2. Bluesky run (53,826 docs, bot-filtered)
3. Update `context/state.md` and `context/task-queue.md`

## Quality checks
- Residual noise rate of the re-clustering (outliers-of-outliers)
- Relevance gate removes known noise themes (music, pets, generic chatter)
- Top of novelty ranking contains themes outside the 34 (Reddit) / 62 (Bluesky)
  existing topics; early-stage weak signals (data-center-style) should surface
