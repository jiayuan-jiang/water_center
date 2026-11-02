# Great Lakes Social Listening

Surfacing emerging ecological and socioeconomic weak signals from public social media discourse, as an input to the [Great Lakes Horizon Scan](https://watercenter.umich.edu) run by the University of Michigan Water Center.

The pipeline collects posts from three platforms, builds a topic model per platform, and scores small "outlier" clusters for relevance, novelty and recency to flag candidate emerging issues for human review.

| Platform | Source | Coverage |
|----------|--------|----------|
| Reddit | [Arctic Shift](https://arctic-shift.photon-reddit.com) archive API | 12 subreddits, 2023-01 to 2026-05 |
| Bluesky | AT Protocol `searchPosts` | 12 queries x 42 months, 2023-01 to 2026-06 |
| Mastodon | Public hashtag timelines | 18 hashtags, 2023-01 to 2026-07 |

## Repository layout

```
scrapers/        Raw collection, one script per platform         -> data/*_raw.jsonl
preprocessing/   Cleaning, language/length/relevance filters, dedup -> data/corpus*.jsonl
analysis/        BERTopic, NMF sub-topics, outlier clustering, similarity networks
llm/             LLM-backed steps (grounded summaries, STEEP tags, outlier candidates, ...)
build/           Converts analysis outputs to JSON for the topic browser
frontend/        React 18 + Vite topic browser (deployed on Vercel)
experiments/     API probes and pilots, not part of the pipeline
context/         Project state, task queue and project plan
spec/            One design note per analysis step
data/            Raw and processed data (not in the repository)
```

## Setup

```bash
conda create -n watercenter python=3.11
conda activate watercenter
pip install -r requirements.txt
```

LLM steps read API keys from a `.env` file in the repository root (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_KEY`). Bluesky search needs `BSKY_USER` and `BSKY_PASS` in the same file. `.env` is git-ignored.

Run every script from the repository root; data paths are relative to it.

## Pipeline

```
scrape -> data/<source>_raw.jsonl -> preprocess -> data/corpus*.jsonl
       -> topic model -> data/topics*/ -> build -> frontend/public/data/
```

Reddit:

```bash
python scrapers/scrape_reddit.py
python scrapers/scrape_comments.py
python preprocessing/preprocess_reddit.py
python analysis/topic_model.py
```

Bluesky and Mastodon:

```bash
python scrapers/scrape_bluesky.py
python preprocessing/preprocess_bluesky.py
python analysis/topic_model.py --corpus data/corpus_bluesky.jsonl --out-dir data/topics_bluesky

python scrapers/scrape_mastodon.py
python preprocessing/preprocess_mastodon.py
python analysis/topic_model.py --corpus data/corpus_mastodon.jsonl --out-dir data/topics_mastodon
```

Emerging-issue (outlier) analysis, per platform:

```bash
python analysis/outlier_analysis.py --platform reddit      # reddit | bluesky | mastodon
python llm/outlier_candidates.py --platform all            # grounded titles and summaries
python build/build_outlier_data.py --platform all
```

Topic browser data:

```bash
python analysis/subtopic_model.py --platform reddit
python llm/grounded_summary.py --platform all
python build/build_docs_data.py --platform reddit
python build/build_trend_data.py --platform all
python build/build_subtopic_data.py --platform all
python analysis/topic_similarity_network.py --all
```

Method details for each step are in [spec/](spec/); current status is in [context/state.md](context/state.md).

The sentiment and emotion scripts (`analysis/sentiment_analysis.py`, `analysis/outlier_emotion.py`, `llm/sentiment_llm.py`, `llm/emotion_llm.py`) and the controversy scoring (`llm/controversy_llm.py`) are outside the scope of the Horizon Scan report.

## Topic browser

```bash
cd frontend
npm install
npm run dev
```

## Author

Jiayuan Jiang · jiayuanj@umich.edu · University of Michigan
