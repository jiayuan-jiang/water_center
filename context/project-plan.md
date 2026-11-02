# Great Lakes Horizon Scan — Social Media Analysis Plan

## Project Context

The U-M Water Center is running a **Great Lakes Horizon Scanning** initiative to proactively identify "weak signals" of emerging ecological and socioeconomic issues before they become crises. A scanning board of ~30 people (scientists, practitioners, tribal nations, First Nations in Canada, government leaders, community members) will meet in late September to review a long list of issues and prioritize 5–10 emerging ones.

Social media analysis is one input channel alongside an expert/public survey and academic literature search. The goal is to capture **organic public discourse** that the survey cannot.

**Key contacts:**
- **Manja** — project lead, primary point of contact
- **Derek** — technical advisor, consult on data/API issues
- **Eric** — collaborator on the social media component

---

## Role

Scrape and analyze social media text to:
1. Discover topics the public is organically discussing related to the Great Lakes
2. Assess attitudes/sentiment toward those topics
3. Identify trends over time (which topics are growing = potential weak signals)

This is **exploratory** (discover unknown issues), not confirmatory (validate known ones).

---

## Scope Decisions (confirmed with Manja)

| Parameter | Decision |
|-----------|----------|
| Primary platform | Reddit |
| Other platforms | Explore feasibility; not blocking |
| Time range | Past 2–3 years |
| Geography | No restriction (location data unreliable) |
| Subject matter | Water-related ecological + socioeconomic issues in Great Lakes basin |

**Platform notes:**
- Twitter/X: $300/month API, ruled out for now
- Bluesky: Liberal-leaning skew, secondary interest only
- LinkedIn: Secondary interest only
- Facebook: To be investigated

---

## Technical Plan

### Step 1 — Data Collection
- **Primary tool:** Arctic Shift API (query by subreddit + time range, no bulk download needed)
- **Backup:** PRAW (Reddit's official Python library) for recent posts
- **Target subreddits:** `r/greatlakes`, `r/michigan`, `r/wisconsin`, `r/ohio`, `r/ontario`, `r/environment`, `r/waterquality` + others TBD
- **API access:** Register a Reddit app at `reddit.com/prefs/apps` (free, instant)

### Step 2 — Topic Modeling
- Use **BERTopic** (preferred over LDA — better semantic clustering, handles noise better)
- Unsupervised clustering to surface naturally emerging topic groups
- Output: ranked topic list with representative posts

### Step 3 — Expert Review
- Topics from Step 2 need human verification — algorithm output can be noisy or nonsensical
- Share results with Manja/scanning board for domain validation

### Step 4 — Sentiment & Trend Analysis
- Per-topic sentiment (positive / negative / neutral)
- Time series: is a topic growing, stable, or seasonal?
- Growing niche topics = candidate weak signals

### Step 5 — (Stretch) Community Analysis
- Bio/profile-based grouping: indigenous community vs. academic vs. general public
- Interesting but acknowledged as difficult — do not block main pipeline on this

---

## Deliverables

1. **Topic list** — primary output, goes to scanning board
2. **Trend charts** — which topics are rising over time
3. **Sentiment summary** — public attitude toward each topic
4. **Method notes** — what worked, what didn't (team is explicitly OK with dead ends)

---

## Key Constraints & Notes

- Team has **no technical expertise** in social media scraping — full ownership of methodology falls to RA
- Team is explicitly open to feedback: *"If something is not feasible, just tell us"*
- This is the **first year** of what will be a recurring 2–3 year cycle — exploratory, not expected to be perfect
- Approximately **10–15 hours/week** allocated to this project
- Derek can help review outputs and suggest search term adjustments; he can also help with coding if needed
