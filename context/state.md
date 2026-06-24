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
| Topic browser | Static HTML/JS → `docs/` (GitHub Pages) |

---

## Data Inventory

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

## Work Status

### Done
- [x] Reddit scraping — posts + comments via Arctic Shift API
- [x] Preprocessing — cleaning, keyword filter, dedup → `corpus.jsonl`
- [x] Guided BERTopic — 34 topics identified
- [x] Word cloud visualizations (overall + 11 key topics)
- [x] Topic browser (`docs/`) with per-topic comment viewer
- [x] Progress report (`progress_report.pdf`)

### In Progress
- [ ] Multi-platform data expansion (see task-queue)

### Blocked / Pending Decision
- Bluesky: draft email to leobalduf team sent (awaiting reply); see `spec/bluesky-data.md`
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
```

---

## Known Issues / Limitations

1. 74% of Reddit posts have no body text — signal comes primarily from comments
2. `r/waterquality` subreddit returned zero results from Arctic Shift
3. No geographic filter — all locations included (location data unreliable)
4. Bluesky search API only reliable for ~30–90 days back; no full historical archive exists
5. Topic -1 (outliers) = 3,717 docs (~44% of corpus) — high noise rate typical for BERTopic on short social media text
