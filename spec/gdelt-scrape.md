# Spec: GDELT News Media Scraping

## Goal
Collect news media coverage of Great Lakes environmental topics via GDELT Full Text Search API to complement Reddit's public discourse data.

---

## What is GDELT

Global Database of Events, Language, and Tone — monitors print, broadcast, and web news in 100+ languages. Historical archive from 1979, updates every 15 minutes. **Free, no API key required.**

This captures the **institutional/media perspective** vs Reddit's **organic public discourse** — a complementary signal for the Horizon Scan.

---

## API

**Base URL:** `https://api.gdeltproject.org/api/v2/doc/doc`

**Key parameters:**
```
query=      keyword or phrase (supports AND, OR, quotes)
mode=       artlist (article list) | timelinevolume | tonechart
startdatetime= YYYYMMDDHHMMSS
enddatetime=   YYYYMMDDHHMMSS
maxrecords= 250 (max per request)
format=     json
sourcelang= eng
```

**Example:**
```
https://api.gdeltproject.org/api/v2/doc/doc?query="Great Lakes"&mode=artlist&maxrecords=250&format=json&startdatetime=20230101000000&enddatetime=20260601000000&sourcelang=eng
```

---

## Scraping Strategy

- **Time range:** 2023-01-01 to present (matches Reddit corpus)
- **Keywords:** Same 6 lake names as Reddit, one query each
- **Pagination:** GDELT doesn't have cursor pagination — use rolling time windows (e.g., monthly) to get around 250-result cap
- **Output:** `data/gdelt_raw.jsonl`

**Monthly window loop:**
```python
for month in months(2023-01, 2026-06):
    for keyword in KEYWORDS:
        fetch(keyword, start=month_start, end=month_end)
        # up to 250 articles per month per keyword
```

**Available fields per article:**
- `url`, `title`, `seendate`, `socialimage`, `domain`, `language`, `sourcecountry`
- Note: **full article text is NOT returned** — only title + URL
- To get body text: must fetch each article URL separately (optional, complex)

---

## Decision Point

Two approaches:
1. **Title-only** — fast, use article titles as short documents; limited NLP signal
2. **Full text** — fetch each article body (scrape URLs); slower, more data, may hit paywalls

**Recommendation:** Start with title-only to assess volume; escalate to full text if volume justifies it.

---

## Corpus Schema (output)

```json
{
  "id": "gdelt_<md5_of_url>",
  "post_id": null,
  "source": "gdelt",
  "author": "domain.com",
  "score": null,
  "created_utc": 1234567890,
  "text": "Article title (or full text if scraped)"
}
```

---

## Notes

- GDELT captures media coverage, not public opinion — interpret differently from Reddit
- May over-represent institutional/government voices
- Good for identifying emerging issues that have crossed into media coverage
- Can also generate `timelinevolume` charts to show media attention over time
