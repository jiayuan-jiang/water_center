# Spec: Controversy Score Definition

## Background

`spec/reddit-further-analysis.md` (Analysis 3) originally specified:

> Controversy score = min(positive%, negative%) × 2 (high when both are high)

This was an ad hoc formula, not sourced from any external definition. Per request,
this doc surveys how "controversy"/polarization is actually measured in the
literature and in production systems, then picks a formula for this project with
justification.

## What the literature actually does

### 1. Graph-based controversy (the academic standard)

**Garimella, De Francisci Morales, Gionis, Mathioudakis — "Quantifying
Controversy on Social Media"** (ACM Trans. Soc. Comput., 2018; earlier version
arXiv:1507.05224, 2015) — [arxiv.org/abs/1507.05224](https://arxiv.org/abs/1507.05224)

- Builds a conversation/interaction graph (who retweets/replies to whom) on a topic
- Partitions it into two sides (e.g. via METIS or a similar graph partitioner)
- Computes **Random Walk Controversy (RWC)**:
  `RWC = P_XX·P_YY − P_YX·P_XY`, where `P_AB` = probability a random walk started
  in partition A ends in partition B. RWC → 1 when the two sides rarely cross-talk
  (polarized), → 0 when they freely mix.
- This is the measure the field treats as canonical — later work (e.g. "A
  Framework for Quantifying Controversy... Biased Random Walk", ResearchGate:
  [10.1109/ASONAM49781.2020.9381457](https://www.researchgate.net/publication/343904049))
  extends it but keeps the graph-based core.
- **Not usable here**: it requires a reply/retweet interaction graph with two
  identifiable sides. Our data is topic-level sentiment percentages with no
  conversation-thread graph — Reddit comment parent/child structure exists in
  principle but isn't in `documents_with_topics.csv`, and Bluesky search results
  have no thread structure at all in our corpus.

### 2. Reddit's own "controversial" sort

Characterized (Reddit has never published the exact formula) across multiple
independent write-ups —
[teamblind discussion](https://www.teamblind.com/post/reddit-whats-the-algorithm-behind-sort-by-controversial-xrwtknhi),
[Hacker News thread](https://news.ycombinator.com/item?id=8586741) — as: rank by
how **balanced** upvotes/downvotes are (roughly `min(ups, downs)`), scaled by
total vote **magnitude**, so 1000-up/100-down ranks lower than 200-up/200-down,
and a 10-vote post never outranks a 2000-vote post at the same ratio. The
"best"/default comment sort, by contrast, is Evan Miller's **Wilson score lower
bound** (["How Not to Sort by Average Rating"](http://www.evanmiller.org/how-not-to-sort-by-average-ratings.html)),
which is the standard fix for "a 2/2 split looks identical to a 500/500 split"
when you naively use a ratio — it discounts small samples via a confidence
interval on the true proportion.

### 3. Sentiment-distribution-based measures (closest to our setting)

Work on polarization from sentiment distributions (e.g. arXiv:2106.09354,
"Retrospective Analysis of Controversial Subtopics on COVID-19 in Japan") uses
**sentiment variance/spread** across a topic's documents as a proxy, but
explicitly notes sentiment std-dev correlates weakly with graph-based controversy
— sentiment alone under-detects "echo chamber" polarization (two internally
uniform but opposite-sentiment clusters can look identical, in aggregate, to
mixed ambivalence). This is a real limitation to flag, not solve — we don't have
per-user/per-cluster structure to distinguish the two cases either.

## Decision

We keep this **sentiment-percentage-based**, not graph-based (no interaction
graph available), and fix two problems in the original formula:

1. **Conflates balance with volume of opinion** — `min(pos,neg) × 2` scales with
   how much non-neutral mass exists, not just how evenly split it is. Topic A
   (pos=40%, neg=40%, neutral=20%) and Topic B (pos=10%, neg=10%, neutral=80%)
   are both *perfectly* split 50/50 between positive and negative — equally
   "balanced" in Reddit's sense — but the old formula scores them 80 vs. 20, as
   if B were far less controversial. It isn't less balanced, it's just quieter.
   A **ratio** (`min/max`) gives both 1.0, capturing "evenly split" independent
   of how much of the topic is neutral chatter.
2. **No sample-size guard** — 2 docs at 1-pos/1-neg scores identically to 500 at
   250/250. We don't fold in a Wilson-style confidence discount (that adds a
   second hyperparameter and this is a report-prep heuristic, not a ranking
   system users can game), but we keep `n_docs` alongside the score in the output
   so small-n topics are visibly flagged rather than silently conflated.

**New formula:**
```
opinion_mass = pos_pct + neg_pct
controversy_score = 0                                  if opinion_mass < 5%
                   = min(pos_pct, neg_pct) / max(pos_pct, neg_pct)   otherwise   # in [0, 1]
```
0 = fully one-sided (or no opinion expressed either way), 1 = perfectly split
between positive and negative, independent of how much neutral mass exists.

The `opinion_mass < 5%` floor was added after inspecting actual output: Bluesky's
NOAA/NWS weather-bot topics (already flagged in `task-queue.md` as automated
spam) sit at ~99.6% neutral, with pos/neg each ~0.2% — a near-zero split that the
raw ratio scores as 1.0 ("perfectly controversial"), when the correct read is
"no one is expressing an opinion at all." The floor treats near-total-neutral
topics as non-controversial by definition rather than as a ratio edge case.

Read alongside `n_docs` — treat scores from topics with small `n_docs` (rule of
thumb: < 30, matching this project's own BERTopic `min_cluster_size=30`) as
low-confidence.

## Reddit's native `controversiality` field

`data/comments_raw.jsonl` carries Reddit's own per-comment `controversiality`
flag (platform-computed, formula not published, dropped during
`preprocessing/preprocess_reddit.py`). Joined back in via `analysis/sentiment_analysis.py` as
`pct_reddit_controversial` in `sentiment_by_topic_reddit.csv` (Reddit only — no
Bluesky equivalent exists).

**Correlation with our sentiment-based `controversy_score`: −0.31** (weak,
negative). This is not a bug — the two measure different things. Reddit's flag
fires when a comment's *vote reception* is disputed (roughly equal up/downvotes
on that one comment); our score measures whether a *topic's* documents split
between positive/negative sentiment. A comment can be uncontroversial by votes
(everyone agrees it's good) while still being strongly negative in sentiment
(e.g. "Nestlé is destroying the lake" — near-unanimous upvotes, very negative
sentiment, low vote-controversy). This mirrors the finding in the COVID-Japan
paper above that sentiment-based and interaction-based controversy measures
correlate weakly — confirmed empirically here, not just cited from elsewhere.

## Graph-based pilot (Garimella RWC) — result: not usable as-is

Piloted on 3 Reddit topics with the most thread-concentrated docs (`experiments/controversy_graph_pilot.py`):
Data Centers (T10), Offshore Wind (T15), Waterfront & Tourism (T3). For each,
pulled *all* raw comments (not just topic-filtered ones) from the topic's
threads, built an author-reply graph, bisected the giant component
(`networkx.kernighan_lin_bisection`), and estimated RWC via random-walk
simulation.

| Topic | Docs | Threads | Graph nodes | Giant component | RWC |
|---|---|---|---|---|---|
| T10 Data Centers | 145 | 20 | 1,085 | 96% | 0.438 |
| T15 Offshore Wind | 80 | 13 | 629 | 52% | 0.316 |
| T3 Waterfront & Tourism | 197 | 40 | 3,279 | 95% | 0.486 |

These numbers look plausible in isolation (Garimella's own paper reports ~0.4–0.8
for genuinely controversial topics like abortion/gun control), but a diagnostic
check on T10 shows why they're **not trustworthy**: of the 1,084 distinct
commenters in that topic's threads, only **36 (3.3%) appear in more than one
thread**. The graph is ~20 nearly-disconnected thread-clusters stitched together
by a handful of bridge users. A min-cut bisection on that structure finds
"which thread(s) you commented in," not "which side of a debate you're on" —
and it will produce a moderate-to-high RWC-looking number regardless of whether
real opinion polarization exists (T3, Waterfront & Tourism, has no obvious
ideological axis and still scores highest of the three).

**Root cause**: Garimella's method assumes one continuous, densely
cross-linked conversation (a live Twitter hashtag). Our Reddit topics are
composed of many independent threads spread over 3 years across 12
subreddits — structurally the wrong shape for this method, confirming the
concern raised before piloting, now with numbers instead of a guess.

**Conclusion**: not worth extending to more topics as-is. Revisit only if a
future data source provides a genuinely continuous, densely-linked
conversation graph (unlikely for Reddit's post-then-comment structure; possibly
GDELT-linked social replies, if that ever materializes).

## Final decision (per platform)

- **Reddit** → `pct_reddit_controversial` (platform-native vote-based flag) is
  the controversy metric to use.
- **Bluesky** → no native equivalent is possible: atproto has no downvote, so
  there's no "votes disputed" signal to borrow. Checked whether
  `reply_count`/`like_count` (present in `data/bluesky_raw.jsonl`) could stand
  in for the up/down-vote balance idea (lots of replies relative to likes ≈
  pushback, not agreement) — but 78.5% of posts have `reply_count == 0`,
  because this corpus was built by keyword search over individual posts, not by
  crawling full conversation threads, so there isn't enough reply depth for
  that signal to mean anything. **Bluesky uses the sentiment-ratio
  `controversy_score`** defined above instead — the one measure that's actually
  supported by this platform's data shape.

**Consequence**: the two platforms' controversy numbers are not on the same
scale and must not be compared head-to-head (e.g. "Bluesky topic X is more
controversial than Reddit topic Y" is not a valid claim from these numbers) —
Reddit's is a vote-dispute signal, Bluesky's is a sentiment-split signal. Each
is only meaningful for ranking topics *within* its own platform.

## What changed in the output

`data/analysis/sentiment_by_topic_{platform}.csv` — `controversy_score` column
now uses the ratio formula above instead of `min(pos,neg) × 2`. Recomputed from
the existing doc-level `sentiment_docs_{platform}.csv` (no re-inference needed).
