# Spec: Sub-topic Analysis

_Created: 2026-06-29_

---

## Motivation

Main BERTopic topics tell you **what a topic is** but not **what people are saying** within it or **what their attitude is**. A scanning board member looking at "Fisheries & Invasive Species" still has to read hundreds of comments to understand the discourse.

Sub-topic splitting breaks each main topic into coherent chunks, so that the next step — grounded generation — can produce focused, verifiable summaries per chunk rather than vague overviews of a broad topic.

---

## Pipeline Position

```
corpus.jsonl
    ↓ analysis/topic_model.py
data/topics/documents_with_topics.csv
    ↓ analysis/subtopic_model.py          ← this spec
data/subtopics/overview.json
    ↓ grounded_generation.py     ← next step (see below)
per-subtopic: label + summary + attitude + key quotes
```

---

## Script

`analysis/subtopic_model.py`

```bash
python analysis/subtopic_model.py                    # Reddit
python analysis/subtopic_model.py --platform bluesky # Bluesky (28 labeled topics only)
```

---

## Method: NMF on TF-IDF

Chosen over BERTopic-on-subsets because:
- No re-embedding needed (fast, works on small corpora)
- Reliable at 40–300 doc range
- Keyword quality sufficient for grounded generation input

### Key parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| `min_docs` | 40 | Below this, sub-topics have no statistical meaning |
| `auto_k` | `max(2, min(6, n_docs // 80))` | One sub-topic per ~80 docs |
| `max_df` | 0.5 | Filter words appearing in >50% of a topic's docs (domain-ubiquitous terms) |
| `ngram_range` | (1, 2) | Capture "zebra mussel", "sea lamprey", "pfas contamination" |
| `max_features` | 3000 | Cap vocabulary size |

### Stop words

`sklearn` English stop words + domain noise:

```python
DOMAIN_STOP = {
    # generic corpus noise
    "lake", "lakes", "great", "michigan", "water", "people",
    "like", "just", "don", "ve", "really", "lot", "think",
    "know", "going", "make", "good", "said", "year", "years",
    # URL / link fragments (Bluesky share previews)
    "com", "org", "www", "http", "https", "arti", "article",
    "buff", "ly", "bsky", "social", "bsky social",
    # NOAA / weather bot formatting tokens
    "edt", "cdt", "pm", "am", "kts", "kt", "nm", "5nm",
    "oversized", "186", "185",
}
```

---

## Output

### `data/subtopics/overview.json` (Reddit)
### `data/subtopics_bluesky/overview.json` (Bluesky)

Schema per topic entry:

```json
{
  "topic_id": 2,
  "topic_name": "2_zebra mussels_whitefish_lamprey_mussels",
  "doc_count": 226,
  "n_subtopics": 2,
  "imbalanced_split": false,
  "subtopics": [
    {
      "subtopic_id": 0,
      "keywords": ["mussels", "zebra", "invasive", ...],
      "doc_count": 107,
      "repr_docs": [
        {"id": "...", "text": "...", "score": 42}
      ]
    }
  ]
}
```

`imbalanced_split: true` means the largest sub-topic is >5× the smallest. The smaller sub-topic may be noise but is retained for manual review.

### Per-topic CSVs

`data/subtopics/topic_{N:02d}.csv` — all docs with `subtopic` and `subtopic_score` columns added.

---

## Coverage

### Reddit (25 of 34 topics processed)

Topics 25–33 skipped (< 40 docs each).

Notable sub-topic splits:
- **Topic 2** (Invasive Species): zebra mussels vs. sea lamprey — clean
- **Topic 5** (Beach): general beach access vs. private beach access rights
- **Topic 10** (Data Centers): general data center discussion vs. water cooling systems
- **Topic 14** (Drinking Water): tap water safety vs. bottled water
- **Topic 15** (Wind Energy): turbine construction vs. bird/wildlife impact
- **Topic 17** (Water Levels): level measurement vs. shoreline erosion

### Bluesky (28 labeled topics processed)

Notable splits:
- **Topic 18** (Data Centers): `ai, ai data, draining` emerged as a distinct sub-topic — AI water footprint weak signal confirmed on both platforms
- **Topic 29** (Indigenous): specific tribal communities (Fond du Lac, Red Cliff, Potawatomi, Lac du Flambeau)
- **Topic 31** (Parks): Sleeping Bear / Indiana Dunes / sand dunes / state parks
- **Topic 36** (Shipping): St. Lawrence / Erie Canal / Welland Canal

Known quality issues:
- Topics 5, 27, 48, 49 dominated by automated NOAA weather bot posts → sub-topics reflect geography of weather stations, not discourse. See [known issue in task-queue](../context/task-queue.md#known-issues).
- Some residual URL fragments in keywords (minor, does not affect sub-topic coherence).
- Topic 35 label corrected from "Environmental Advocacy" to "UFO/UAP Sightings Over Great Lakes" in `build/build_docs_data.py`.

---

## Next Step: Grounded Generation

The output of this step feeds directly into `grounded_generation.py` (not yet written).

For each sub-topic, the LLM will receive `keywords` + `repr_docs` from `overview.json` and produce:

```json
{
  "label": "Sea Lamprey Population Control",
  "summary": "...",
  "attitude": "...",
  "key_quotes": [{"id": "...", "text": "..."}]
}
```

The `label` is generated here rather than in a separate step to ensure semantic consistency between label and summary.
