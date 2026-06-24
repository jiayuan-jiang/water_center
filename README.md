# Great Lakes Social Listening

Identifying emerging issues and weak signals in Great Lakes public discourse through Reddit topic modeling — a component of the U-M Water Center Horizon Scan initiative.

## Overview

This project collects and analyzes public Reddit discourse related to the Great Lakes basin to surface topics and weak signals that may inform the [Great Lakes Horizon Scan](https://watercenter.umich.edu) process. The analysis pipeline covers data collection, preprocessing, and unsupervised topic modeling using BERTopic.

**Data source:** Reddit (via [Arctic Shift](https://arctic-shift.photon-reddit.com) archive API)  
**Time range:** January 2023 — May 2026  
**Corpus:** 8,441 filtered comments across 12 subreddits  
**Topics identified:** 34

## Repository Structure

```
├── scrape_reddit.py       # Collect posts from Reddit via Arctic Shift API
├── scrape_comments.py     # Collect comments for each post
├── preprocess.py          # Clean and filter raw comments
├── topic_model.py         # Guided BERTopic analysis
├── wordcloud_viz.py       # Generate word cloud visualizations
├── build_docs_data.py     # Build JSON data for the topic browser
├── requirements.txt       # Python dependencies
├── docs/                  # Topic browser (GitHub Pages)
│   ├── index.html
│   └── data/
└── data/                  # Raw and processed data (not tracked in git)
    ├── posts_raw.jsonl
    ├── comments_raw.jsonl
    ├── corpus.jsonl
    └── topics/
```

## Setup

```bash
conda create -n watercenter python=3.11
conda activate watercenter
pip install -r requirements.txt
```

## Pipeline

```bash
python scrape_reddit.py       # ~30 min
python scrape_comments.py     # ~90 min
python preprocess.py
python topic_model.py
python wordcloud_viz.py
python build_docs_data.py
```

## Topic Browser

The `docs/` folder contains a static topic browser. To run locally:

```bash
cd docs
python3 -m http.server 8080
# open http://localhost:8080
```

## Author

Jiayuan Jiang · jiayuanj@umich.edu  
University of Michigan
