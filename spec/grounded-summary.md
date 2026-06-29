# Grounded Summary Generation

## Purpose

For each sub-topic cluster identified by NMF (see `spec/subtopic-analysis.md`), call an LLM to produce a human-readable, source-grounded description. Every claim must be traceable to a specific document ID.

---

## Input

| File | Contents |
|------|----------|
| `data/subtopics/overview.json` | Reddit: 25 topics × 58 subtopics, each with `keywords` + `repr_docs` (3 docs with `id`, `text`, `score`) |
| `data/subtopics_bluesky/overview.json` | Bluesky: 28 topics × 120 subtopics, same schema |

---

## Output

| File | Contents |
|------|----------|
| `data/subtopics/grounded_summary.json` | Reddit overview + `generated` field per subtopic |
| `data/subtopics_bluesky/grounded_summary.json` | Bluesky overview + `generated` field per subtopic |

### `generated` schema (per subtopic)

```json
{
  "label":      "Short descriptive label (4-7 words)",
  "summary":    "2-3 sentences. Every claim cites [doc_id] inline.",
  "attitude":   "Dominant sentiment/stance phrase",
  "key_quotes": [
    {
      "id":    "<document id>",
      "quote": "<verbatim substring from source text, ≤20 words>",
      "note":  "Why this quote is representative"
    }
  ]
}
```

---

## Script

`grounded_summary.py`

```
usage: python grounded_summary.py [--platform reddit|bluesky|all] [--model MODEL] [--dry-run]

options:
  --platform   Which dataset to process (default: reddit)
  --model      Gemini model ID (default: gemini-2.5-flash)
  --dry-run    Skip API calls; write placeholder data to verify logic
```

### Resumability

Progress is checkpointed after each subtopic:
- `data/subtopics/.grounded_checkpoint.json`
- `data/subtopics_bluesky/.grounded_checkpoint.json`

Re-running the script skips already-completed subtopics. To restart from scratch, delete the checkpoint file.

---

## LLM Configuration

| Parameter | Value |
|-----------|-------|
| Provider | Google Gemini |
| Model | `gemini-2.5-flash` |
| Max tokens | 600 |
| Rate limit handling | 0.3s sleep between calls; 3 retries with 60/120/180s backoff on quota errors |

**API key**: set `GEMINI_API_KEY` environment variable before running.

### Prompt strategy

System prompt establishes the grounding rule: output only what is present in the provided documents, cite every claim with `[doc_id]`, use verbatim quotes only. The user turn provides:
- Parent topic name
- Top 8 subtopic keywords
- Cluster document count
- 3 representative documents (id + text + score)

---

## Run log

| Date | Platform | Subtopics | Errors | Model |
|------|----------|-----------|--------|-------|
| 2026-06-29 | Reddit | 58/58 | 0 | gemini-2.5-flash |
| 2026-06-29 | Bluesky | 120/120 | 0 | gemini-2.5-flash |

---

## Re-running after data updates

If subtopic analysis is re-run (e.g., new corpus data), delete both checkpoint files and re-run:

```bash
rm data/subtopics/.grounded_checkpoint.json
rm data/subtopics_bluesky/.grounded_checkpoint.json
export GEMINI_API_KEY=...
python grounded_summary.py --platform all
```

---

## Dependencies

- `google-genai` Python package (`pip install google-genai`)
- Subtopic analysis complete: `data/subtopics/overview.json`, `data/subtopics_bluesky/overview.json`
