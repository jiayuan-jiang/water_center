# CLAUDE.md — Great Lakes Social Listening

## Project in One Line
Scrape + analyze public social media discourse to surface emerging ecological/socioeconomic weak signals for the U-M Water Center Great Lakes Horizon Scan.

---

## Context Loading Protocol

At the start of every session, read in this order:
1. `CLAUDE.md` (this file) — rules and orientation
2. `context/state.md` — current tech stack, completed/blocked work
3. `context/task-queue.md` — what to do next

Before touching any script, check `context/task-queue.md` for the current in-progress task and its linked spec in `spec/`.

---

## Multi-Session Worktree Protocol

**Every task runs in its own git worktree — never work directly on `main` in the primary checkout.** Multiple Claude Code sessions run in parallel on this project; without worktrees, sessions silently stomp on each other's edits to the same files (this happened — see `context/state.md` history around 2026-08-19).

- At the start of any task, call `EnterWorktree` before editing anything (skip only for a pure read/research task that touches no files).
- Give the worktree a name that reflects the task (e.g. `EnterWorktree({ name: "help-guide-comments-filter" })`).
- When the task is done: commit inside the worktree, merge/push from there, then `ExitWorktree` — `action: "remove"` once merged, `action: "keep"` if the work should stay around for later.
- This applies to every session, not just ones the user tags "worktree" — treat this file as the standing instruction that triggers `EnterWorktree`'s usage condition.

---

## Project Structure

```
├── scrapers/               # Raw collection → data/*_raw.jsonl
│   ├── scrape_reddit.py        # Arctic Shift API → posts_raw.jsonl
│   ├── scrape_comments.py      # Arctic Shift API → comments_raw.jsonl
│   ├── scrape_bluesky.py       # atproto searchPosts → bluesky_raw.jsonl
│   └── scrape_mastodon.py      # hashtag timelines → mastodon_raw.jsonl
├── preprocessing/          # raw JSONL → corpus*.jsonl
│   ├── preprocess_reddit.py
│   ├── preprocess_bluesky.py
│   └── preprocess_mastodon.py
├── analysis/               # Local modeling (no LLM calls)
│   ├── topic_model.py          # BERTopic
│   ├── subtopic_model.py       # NMF sub-topics
│   ├── outlier_analysis.py     # outlier micro-clusters + emerging-issue scoring
│   ├── topic_similarity_network.py
│   ├── sentiment_analysis.py, outlier_emotion.py   # RoBERTa sentiment/emotion
│   └── wordcloud_viz.py
├── llm/                    # LLM-backed steps (grounded_summary.py holds shared helpers)
│   ├── grounded_summary.py, outlier_candidates.py
│   ├── controversy_llm.py, steep_tag.py
│   └── sentiment_llm.py, emotion_llm.py
├── build/                  # Analysis outputs → frontend/public/data/ JSON
├── experiments/            # API probes and pilots, not part of the pipeline
├── frontend/               # React 18 + Vite topic browser (deployed on Vercel)
├── docs/                   # Submodule: GitHub Pages site
├── context/                # Session state + project plan (tracked)
│   ├── state.md
│   ├── task-queue.md
│   └── project-plan.md
├── spec/                   # One file per task, linked from task-queue
├── data/                   # NOT in repo — raw + processed data
└── requirements.txt
```

---

## Coding Rules

- **Python 3.11**, conda env `watercenter`
- All data files go under `data/` — never commit them (already in .gitignore)
- New platform scrapers follow the same pattern as `scrapers/scrape_reddit.py`: paginate to JSONL, resumable via checkpoint, respect rate limits with `time.sleep`
- New corpus sources must merge into `data/corpus.jsonl` with the same schema: `{id, post_id, subreddit/source, author, score, created_utc, text}`
- No comments in code unless the WHY is non-obvious

---

## Data Pipeline Order

```
[scrape] → raw JSONL → [preprocess] → corpus.jsonl → [topic_model] → data/topics/ → [build_docs_data] → docs/data/
```

When adding a new data source (e.g., Bluesky, GDELT):
1. Write a dedicated scraper → `data/<source>_raw.jsonl`
2. Write or extend preprocess to filter/clean → append to `data/corpus.jsonl`
3. Re-run `analysis/topic_model.py` on merged corpus
4. Re-run `build/build_docs_data.py`

---

## Key Contacts

| Person | Role |
|--------|------|
| Manja | Project lead, primary contact |
| Derek | Technical advisor |
| Eric | Social media analysis collaborator |

---

## Session End Protocol

After completing significant work, update:
- `context/state.md` — reflect any new completed work or blockers
- `context/task-queue.md` — move tasks to correct status
