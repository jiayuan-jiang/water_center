# Task Queue
_Last updated: 2026-06-24 (temporal trend data generation done)_

Format: `- [ ] Task title — [spec](../spec/filename.md)`

---

## In Progress

_(none)_

---

## Pending

### Data Expansion

- [ ] **Bluesky topic labeling** — [spec](../spec/bluesky-data.md)
  - 62 topics in `data/topics_bluesky/topic_summary.csv`
  - Confirmed noise: topic 9 (music), 11 (bsky artifacts), 16 (books), 34 (dogs)
  - Next: label remaining topics, then run `build_docs_data.py` for Bluesky browser

- [ ] **GDELT news media scraping** — [spec](../spec/gdelt-scrape.md)
  - Free full-text search API, covers 1979–present
  - Keywords: same as Reddit (lake names + environmental terms)
  - Output: `data/gdelt_raw.jsonl`

- [ ] **YouTube comments scraping** (stretch) — no spec yet
  - Target: videos from NOAA, Alliance for the Great Lakes, EPA, etc.
  - Tool: YouTube Data API (free, requires Google Cloud project)

### Analysis (Reddit Topics — Further Analysis)

_Full spec: [spec/reddit-further-analysis.md](../spec/reddit-further-analysis.md)_

- [ ] **Temporal trend interpretation — narrative** ⭐ — [spec](../spec/reddit-further-analysis.md#analysis-1--temporal-trend-interpretation-high-priority)
  - Data generation complete: `docs/data/reddit_topic_trends.json` (34 topics × 41 months, LOESS-smoothed)
  - Rendering spec written: `docs/data/reddit_topic_trends.md`
  - **Blocked:** narrative interpretation pending feedback from Manja on which topics to highlight

- [ ] **Temporal trend — frontend rendering**
  - Render `reddit_topic_trends.json` as bar + LOESS chart in topic browser
  - Rendering spec: `docs/data/reddit_topic_trends.md`
  - No spec file yet; defer until narrative direction confirmed

- [ ] **Outlier cluster (-1) sub-clustering** ⭐ — [spec](../spec/reddit-further-analysis.md#analysis-2--outlier-cluster--1-sub-clustering-high-priority)
  - Re-run BERTopic on 3,717 noise docs with looser params (min_cluster_size=10)
  - May reveal hidden weak signals too small for original model

- [ ] **Sentiment analysis per topic** — [spec](../spec/reddit-further-analysis.md#analysis-3--sentiment-analysis-per-topic-medium-priority)
  - Model: `cardiffnlp/twitter-roberta-base-sentiment`
  - Output: per-topic positive/negative/neutral % + controversy score

- [ ] **Subreddit × topic geographic matrix** — [spec](../spec/reddit-further-analysis.md#analysis-4--subreddit--topic-geographic-matrix-medium-priority)
  - Heatmap: which topics are local vs. cross-regional signals
  - Output: `data/analysis/subreddit_topic_matrix.csv` + heatmap PNG

- [ ] **Engagement analysis (score per topic)** — [spec](../spec/reddit-further-analysis.md#analysis-5--engagement-analysis-medium-priority)
  - Rank topics by mean comment score; surface top-scored examples
  - Output: `data/analysis/topic_engagement.csv`

- [ ] **Topic semantic similarity network** — [spec](../spec/reddit-further-analysis.md#analysis-6--topic-semantic-similarity-network-low-priority)
  - Cosine similarity on BERTopic centroid embeddings → network/dendrogram
  - Helps group related topics for the report

- [ ] **STEEP categorization** — [spec](../spec/reddit-further-analysis.md#analysis-7--steep-categorization-low-priority-report-prep)
  - Map 34 topics to Social/Technological/Economic/Environmental/Political tags
  - Output: `data/analysis/topic_steep.csv`

- [ ] **Multi-platform corpus merge** — no spec yet
  - Merge Reddit + Bluesky (if obtained) + GDELT into unified `corpus.jsonl`
  - Add `source` field to schema
  - Re-run topic_model.py on merged corpus

### Deliverables

- [ ] **Scanning board report** — no spec yet
  - Audience: ~30 practitioners, scientists, tribal representatives, government
  - Format: TBD with Manja (likely slide deck + topic browser demo)
  - Deadline: before late September 2026 workshop

---

## Done

- [x] Reddit posts scraping (`scrape_reddit.py`) — 2,179 posts
- [x] Reddit comments scraping (`scrape_comments.py`) — 42,500 comments
- [x] Preprocessing pipeline (`preprocess.py`) — 8,441 corpus docs
- [x] BERTopic topic modeling (`topic_model.py`) — 34 topics
- [x] Word cloud visualizations (`wordcloud_viz.py`)
- [x] Topic browser JSON build (`build_docs_data.py`)
- [x] Static topic browser (`docs/index.html`) → rewritten as React app (`frontend/`)
- [x] Progress report (`progress_report.pdf`)
- [x] Platform feasibility research (LinkedIn → ruled out; Twitter/X → ruled out; Bluesky → limited; GDELT → promising)
- [x] Bluesky archive research (no Arctic Shift equivalent; leobalduf Firehose logs are best available option)
- [x] Email sent to leobalduf (Leonhard Balduf, TU Darmstadt) — 2026-06-24
- [x] Bluesky API live test — since/until params work, 2023 data accessible, auth required
- [x] Context management system created (CLAUDE.md, context/, spec/, memory/)
- [x] Bluesky scraping (`scrape_bluesky.py`) — 258,069 raw posts, 12 queries × 42 months
- [x] Bluesky preprocessing (`preprocess_bluesky.py`) — 125,226 corpus docs
- [x] Bluesky BERTopic (`topic_model.py --corpus ... --out-dir ...`) — 62 topics
- [x] Reddit temporal trend data generation (`build_trend_data.py`) — `docs/data/reddit_topic_trends.json`, 34 topics × 41 months, LOESS frac=0.35
- [x] Bluesky temporal trend data generation (`build_trend_data.py --platform bluesky`) — `docs/data/bluesky_topic_trends.json`, 28 labeled topics × 42 months, LOESS frac=0.35
