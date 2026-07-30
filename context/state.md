# Project State Snapshot
_Last updated: 2026-07-30 (topic similarity network)_

---

## Tech Stack

| Layer | Tool / Version |
|-------|---------------|
| Language | Python 3.11 |
| Conda env | `watercenter` |
| Data collection | `requests` + Arctic Shift API (no auth) |
| NLP / Topic Modeling | `bertopic>=0.16`, `sentence-transformers>=2.7` |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformer) |
| Dimensionality reduction | `umap-learn>=0.5.6` |
| Clustering | `hdbscan>=0.8.33` |
| Keyword representation | `KeyBERTInspired` |
| Vectorizer | `CountVectorizer` (ngram 1–2, min_df=5) |
| Data format | JSONL (raw), CSV (topic outputs) |
| Visualization | `plotly` (interactive), `wordcloud` + `matplotlib` (PNG) |
| Trend smoothing | `statsmodels` (LOESS via `lowess`) |
| Topic browser | React 18 + Vite 5 → builds to `docs/` (GitHub Pages) |

---

## Bluesky Data Inventory

| File | Records | Notes |
|------|---------|-------|
| `data/bluesky_raw.jsonl` | 258,069 | 12 queries × 42 months (2023-01 to 2026-06) |
| `data/corpus_bluesky.jsonl` | 125,226 | After lang/length/relevance/dedup filters |
| `data/topics_bluesky/topic_summary.csv` | 63 rows | 62 topics + outlier cluster (-1) |
| `data/topics_bluesky/documents_with_topics.csv` | 125,226 rows | Each doc with assigned topic |

Outlier rate: 53,826 / 125,226 = 43% (similar to Reddit's 44%)
Notable noise topics: 9 (music), 11 (bsky artifacts), 16 (books), 34 (dogs)
Topic 0 is anomalously large (33,659 docs = 27%) — catch-all general discussion

---

## Reddit Data Inventory

| File | Records | Notes |
|------|---------|-------|
| `data/posts_raw.jsonl` | 2,179 | Reddit posts, Jan 2023–May 2026 |
| `data/comments_raw.jsonl` | 42,500 | Comments for all posts with num_comments > 0 |
| `data/corpus.jsonl` | 8,441 | Cleaned, filtered, deduplicated comments |
| `data/topics/topic_summary.csv` | 35 rows | 34 topics + outlier cluster (-1) |
| `data/topics/documents_with_topics.csv` | 8,441 rows | Each doc with assigned topic |
| `data/reddit_scrape.md` | — | Scraping methodology notes |

### Subreddit breakdown (posts)
r/Michigan 756 · r/ontario 235 · r/chicago 225 · r/minnesota 214 · r/wisconsin 196 · r/GreatLakes 188 · r/Ohio 150 · r/environment 105 · r/illinois 65 · r/Indiana 35 · r/sustainability 6 · r/ecology 4

---

## Topics Identified (34)

Human-labeled in `build_docs_data.py`:

| ID | Label |
|----|-------|
| 0 | General Great Lakes Discussion |
| 2 | Invasive Species |
| 6 | Water Temperature |
| 7 | Climate Change & Seasonal Shifts |
| 8 | Ice Cover & Ice Fishing |
| 9 | PFAS & Chemical Contamination |
| 10 | Data Centers & Water Consumption ← notable weak signal |
| 14 | Drinking Water Safety |
| 15 | Offshore Wind Energy |
| 17 | Lake Water Levels |
| 29 | Algal Blooms |
| 32 | Water Privatization (Nestlé) |
| … | (34 total, see `build_docs_data.py` TOPIC_LABELS) |

---

## Sub-topic Data

| File | Contents |
|------|----------|
| `data/subtopics/overview.json` | Reddit: 25 topics with NMF sub-topics, keywords, repr_docs |
| `data/subtopics/topic_{N:02d}.csv` | Per-topic doc assignments with `subtopic` + `subtopic_score` |
| `data/subtopics_bluesky/overview.json` | Bluesky: 28 labeled topics, same schema |
| `data/subtopics_bluesky/topic_{N:02d}.csv` | Per-topic Bluesky doc assignments |
| `subtopic_model.py` | Generator; `--platform reddit\|bluesky` |
| `spec/subtopic-analysis.md` | Method, parameters, quality review |

`auto_k` formula: `max(2, min(6, n_docs // 80))` — one sub-topic per ~80 docs.
`imbalanced_split: true` when largest/smallest sub-topic ratio > 5× (flagged, not removed).

---

## Trend Data

| File | Contents |
|------|----------|
| `docs/data/reddit_topic_trends.json` | 34 topics × 41 months; arrays: count, total, share, loess |
| `docs/data/bluesky_topic_trends.json` | 28 labeled topics × 42 months; same schema |
| `docs/data/reddit_topic_trends.md` | Schema reference + rendering spec (bar + LOESS), applies to both files |
| `build_trend_data.py` | Generator; `--platform reddit\|bluesky\|all` |

Key observations (Data Centers topic):
- Reddit T10: zero activity 2023-06 through 2025-07, sudden emergence 2025-08, peak 2025-12 (64 docs)
- Bluesky T18: gradual growth from 2024-01, sustained high activity from 2025-08 onward (708 docs total, 30 active months)

Narrative interpretation pending stakeholder feedback from Manja.

---

## Outlier Emerging-Issues Analysis

Spec: `spec/outlier-emerging-issues.md` — operationalizes the meeting definition of
"emerging issue" as relevance × novelty × recency scoring on outlier micro-clusters.

| File | Contents |
|------|----------|
| `outlier_analysis.py` | Stage 1+2: re-cluster topic -1 docs (HDBSCAN 10/5), score clusters |
| `outlier_candidates.py` | Stage 3: Gemini grounded candidate list (Greta-compatible md table) |
| `data/analysis/outlier_subclusters_reddit.csv` | 78 micro-clusters with scores |
| `data/analysis/outlier_overview_reddit.json` | 66 relevance-passing clusters + repr docs |

Bluesky run (2026-07-22, same params as Reddit):
- Input filters (bluesky only): expanded bot blocklist (+5 handles, +regex for
  *.nws-bot.us / *.weather.im / "bot" substring, −3,421 docs), African Great Lakes
  disambiguation (−107), normalized-text dedup incl. same-author near-dups (−539)
- 49,759 docs → 741 micro-clusters, residual 52%, 431 pass relevance ≥ 0.3
- Top signals: Saugeen First Nation beach land return, Great Lakes Cheese wastewater
  (Ischua Creek), FirstEnergy bribery × Lake Erie offshore wind, Muskegon Lake AOC
  delisting, research-vessel "black goo"
- Known residue: viral factoid repost clusters (salt mines, Superior Shoal) survive
  dedup because they are paraphrases — left for LLM/human triage

Reddit pilot results (2026-07-22):
- 3,717 outlier docs → 78 micro-clusters, residual noise 41%
- Relevance gate (≥0.3) passes 66/78; rejected clusters are genuine noise (traffic, weddings, scenery)
- Top candidate: combined sewer overflow / stormwater (15 docs, first seen 2025-04, 93% recent)
- Other notables: golf course water use, cruise ship pollution, Lake Erie odor events
- Borderline: cluster 63 "light pollution" at relevance 0.295 just misses the 0.3 gate — mixed with night photos; revisit threshold if needed

---

## Topic Similarity Networks

`topic_similarity_network.py` — re-embeds each topic/outlier-cluster's actual assigned
docs (sampled up to 80/node) with `all-MiniLM-L6-v2`, mean-pools into a centroid,
computes pairwise cosine similarity, keeps edges >= threshold (default 0.6, no node
filtering — full node sets kept per Manja/team review need to see everything).

| Combo | Nodes | Edges (>=0.6) | Output |
|-------|-------|---------------|--------|
| Reddit topics | 34 | 86 | `frontend/public/data/network/reddit/topics.json` |
| Reddit outliers | 66 | 760 | `frontend/public/data/network/reddit/outliers.json` |
| Bluesky topics | 28 | 92 | `frontend/public/data/network/bluesky/topics.json` |
| Bluesky outliers | 431 | 13,942 | `frontend/public/data/network/bluesky/outliers.json` |

Bluesky outliers is dense by design (431 nodes) — frontend ships a live "min
similarity" slider (0.6-0.95) so the graph can be decluttered interactively without
re-fetching data. Rendered via a new "Similarity Network" tab embedded alongside the
existing List tab on both the Topics and Outlier Signals pages
(`frontend/src/components/NetworkGraph.jsx`, uses `d3-force` for one-shot layout +
plain SVG for rendering, no animation loop). Re-run `python topic_similarity_network.py
--all` after any topic/outlier re-labeling to refresh.

---

## Work Status

### Done
- [x] Reddit scraping — posts + comments via Arctic Shift API
- [x] Preprocessing — cleaning, keyword filter, dedup → `corpus.jsonl`
- [x] Guided BERTopic — 34 topics identified
- [x] Word cloud visualizations (overall + 11 key topics)
- [x] Topic browser (`docs/`) with per-topic comment viewer
- [x] Progress report (`progress_report.pdf`)
- [x] Bluesky scraping — 258,069 raw posts via atproto searchPosts (12 queries × 42 months)
- [x] Bluesky preprocessing — 125,226 corpus docs → `corpus_bluesky.jsonl`
- [x] Bluesky BERTopic — 62 topics → `data/topics_bluesky/`
- [x] Topic browser rewritten in React 18 + Vite 5 (`frontend/`) — builds to `docs/`; multi-platform toggle, breadcrumb nav, platform-aware comment cards
- [x] Reddit temporal trend data — `docs/data/reddit_topic_trends.json` (all 34 topics, LOESS-smoothed, schema documented)
- [x] Topic similarity networks (both platforms x topics/outliers) — `topic_similarity_network.py` + frontend "Similarity Network" tab, see section above

### Done (continued)
- [x] Sub-topic analysis — NMF on TF-IDF; Reddit 25 topics + Bluesky 28 topics → `data/subtopics*/overview.json`
- [x] Bluesky Topic 35 label corrected: "Environmental Advocacy" → "UFO/UAP Sightings Over Great Lakes"
- [x] Grounded summary generation — Gemini 2.5 Flash; Reddit 58 + Bluesky 120 subtopics → `data/subtopics*/grounded_summary.json`; spec: `spec/grounded-summary.md`

### Done (outlier emerging-issues, 2026-07-22)
- [x] Stage 1+2 both platforms — Reddit 66 + Bluesky 431 passing clusters
- [x] Stage 3 grounded summaries — OpenAI gpt-4o-mini (not Gemini; key in `.env`), 497/497, 0 errors
- [x] Frontend outlier browser — platform → mode (Topics | Outlier Signals) → cluster detail
  with scores, monthly bars, grounded summary + cite-jump, full doc list
- [x] `build_outlier_data.py` → `frontend/public/data/outliers/`; deployed via commit ff950dd

### In Progress
- [ ] Team review of 497 outlier clusters on the website (E/K/N triage)

### Blocked / Pending Decision
- Temporal trend narrative: data ready, interpretation pending feedback from Manja
- GDELT: not yet started, scoped in task-queue
- LinkedIn: ruled out (no archive, ToS barriers)
- Twitter/X: ruled out ($300/month API)

---

## Key Configuration

```python
# Time range (scrape_reddit.py)
THREE_YEARS_AGO = int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())

# BERTopic (topic_model.py)
UMAP:   n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42
HDBSCAN: min_cluster_size=30, min_samples=10
Vectorizer: ngram_range=(1,2), stop_words="english", min_df=5

# Corpus filter (preprocess.py)
MIN_WORDS = 15

# Trend smoothing (build_trend_data.py)
LOESS_FRAC = 0.35
```

---

## Known Issues / Limitations

1. 74% of Reddit posts have no body text — signal comes primarily from comments
2. `r/waterquality` subreddit returned zero results from Arctic Shift
3. No geographic filter — all locations included (location data unreliable)
4. Bluesky search API only reliable for ~30–90 days back; no full historical archive exists
5. Topic -1 (outliers) = 3,717 docs (~44% of corpus) — high noise rate typical for BERTopic on short social media text
6. Reddit monthly corpus volume is uneven (range: 43–231 docs/month) — normalization via share is essential for trend comparison
