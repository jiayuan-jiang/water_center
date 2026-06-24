# Project State Snapshot
_Last updated: 2026-06-24_

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
28 valid topics labeled (in `build_docs_data.py` `BLUESKY_TOPIC_LABELS`) → `docs/data/bluesky/`
34 noise/off-topic topics excluded (sports, politics, fiction, African Great Lakes false positives, etc.)
Topic 0 is anomalously large (33,659 docs = 27%) — catch-all general discussion; labeled and kept
Topic 18 = "Data Centers & AI Water Consumption" — 634 posts, key weak signal (confirmed cross-platform with Reddit T10)
Notable Bluesky-only signals: microplastics (T46), wildfire smoke (T50), Indigenous water rights (T29), nuclear waste (T43)

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

## Trend Data (Reddit)

| File | Contents |
|------|----------|
| `docs/data/reddit_topic_trends.json` | 34 topics × 41 months; arrays: count, total, share, loess |
| `docs/data/reddit_topic_trends.md` | Schema reference + rendering spec (bar + LOESS) |
| `build_trend_data.py` | Generator script; re-run to refresh |

Key observation from T10 (Data Centers): zero activity 2023-06 through 2025-07, sudden emergence 2025-08, peak 2025-12 (64 docs, 42% of monthly corpus). Narrative interpretation pending stakeholder feedback from Manja.

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
- [x] Topic browser rewritten in React 18 + Vite 5 (`frontend/`) — 3-level nav (Platform Select → Topic List → Topic Detail), breadcrumb, platform-aware cards
- [x] Reddit temporal trend data — `docs/data/reddit_topic_trends.json` (all 34 topics, LOESS-smoothed, schema documented)
- [x] Bluesky topic labeling — 28 valid topics labeled, 34 noise topics excluded; `docs/data/bluesky/` generated
- [x] Reddit ↔ Bluesky label alignment — 3 labels unified (Climate Change, Wildlife, EPA); deliberate differences documented

### In Progress
_(none)_

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
