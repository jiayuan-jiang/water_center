"""
Generate word clouds from BERTopic results for PPT presentation.
Produces:
  - overall word cloud (all topics combined)
  - top-10 individual topic word clouds
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from wordcloud import WordCloud, STOPWORDS
from pathlib import Path
from collections import Counter
import re

OUT_DIR = Path("data/topics")

# ── Custom stopwords ──────────────────────────────────────────────────────────
EXTRA_STOPS = {
    # overly generic verbs
    "will", "go", "going", "get", "got", "getting", "take", "taking", "took",
    "make", "making", "made", "come", "coming", "came", "look", "looking",
    "looked", "think", "thinking", "thought", "know", "knowing", "knew",
    "say", "said", "saying", "see", "seeing", "saw", "want", "wanted",
    "need", "needed", "use", "used", "using", "put", "keep", "kept",
    "try", "trying", "tried", "find", "found", "feel", "felt",
    # filler words
    "like", "just", "really", "actually", "pretty", "quite", "little",
    "lot", "lots", "much", "many", "well", "also", "even", "still",
    "already", "always", "never", "maybe", "sure", "around", "along",
    "back", "way", "time", "year", "years", "day", "days", "new", "right",
    "first", "last", "big", "long", "different", "another", "anything",
    "something", "nothing", "everything", "someone", "everyone",
    # pronouns / conjunctions handled poorly
    "they", "them", "their", "there", "these", "those", "that", "this",
    "with", "from", "have", "been", "more", "than", "about", "would",
    "could", "should", "might", "may", "part", "point", "end",
    # lake names (too dominant, obscure specific topics)
    "lake", "lakes", "great",
    # state names
    "michigan", "ohio", "ontario", "wisconsin", "chicago", "minnesota",
    "illinois", "indiana", "toronto", "duluth",
    # reddit artifacts
    "don", "ve", "ll", "re", "didn", "isn", "wasn", "isn", "im",
    "ive", "id", "nt",
    # misc noise
    "north", "south", "side", "home", "house", "city", "area", "place",
    "state", "local", "region", "amount", "number",
    "one", "people", "good", "now", "every", "things", "less", "mean",
    "means", "though", "without", "likely", "better", "across", "done",
    "help", "give", "live", "next", "old", "kind", "work", "let",
    "far", "near", "small", "large", "cool", "kid", "friend", "west",
    "east", "seen", "bit", "etc", "lol", "money", "job", "cost",
    "problem", "issue", "risk", "life", "world", "name", "remember",
    "drive", "stop", "away", "human", "probably", "decade",
}
STOPWORDS_ALL = STOPWORDS | EXTRA_STOPS

# ── Load topic-assigned documents ─────────────────────────────────────────────
df = pd.read_csv(OUT_DIR / "documents_with_topics.csv")
df_topics = df[df["topic"] != -1].copy()
print(f"Documents in topics: {len(df_topics):,}")

# ── 1. OVERALL word cloud ─────────────────────────────────────────────────────
all_text = " ".join(df_topics["text"].dropna().tolist())

wc_overall = WordCloud(
    width=2400,
    height=1350,
    background_color="white",
    colormap="Blues",
    stopwords=STOPWORDS_ALL,
    max_words=150,
    collocations=True,
    prefer_horizontal=0.85,
    min_font_size=12,
).generate(all_text)

fig, ax = plt.subplots(figsize=(16, 9))
ax.imshow(wc_overall, interpolation="bilinear")
ax.axis("off")
ax.set_title(
    "Great Lakes Public Discourse — Reddit (2023–2026)",
    fontsize=22, fontweight="bold", pad=20, color="#1a3a5c"
)
plt.tight_layout()
plt.savefig(OUT_DIR / "wordcloud_overall.png", dpi=200, bbox_inches="tight")
plt.close()
print("Saved: wordcloud_overall.png")

# ── 2. Individual word clouds for key topics ──────────────────────────────────
KEY_TOPICS = {
    2:  ("Invasive Species",             "YlGn"),
    6:  ("Water Temperature",            "PuBu"),
    7:  ("Climate Change",               "RdPu"),
    8:  ("Ice Cover & Ice Fishing",      "Blues"),
    9:  ("PFAS & Chemical Pollution",    "OrRd"),
    10: ("Data Centers & Water Use",     "Purples"),
    14: ("Drinking Water Safety",        "GnBu"),
    15: ("Offshore Wind Energy",         "YlOrBr"),
    17: ("Water Levels",                 "BuGn"),
    29: ("Algal Blooms",                 "Greens"),
    32: ("Water Privatization (Nestlé)", "Oranges"),
}

for tid, (label, cmap) in KEY_TOPICS.items():
    subset = df_topics[df_topics["topic"] == tid]
    if subset.empty:
        continue
    text = " ".join(subset["text"].dropna().tolist())
    count = len(subset)

    wc = WordCloud(
        width=2400, height=1350,
        background_color="white",
        colormap=cmap,
        stopwords=STOPWORDS_ALL,
        max_words=100,
        collocations=True,
        prefer_horizontal=0.8,
        min_font_size=14,
    ).generate(text)

    fig, ax = plt.subplots(figsize=(16, 9))
    fig.patch.set_facecolor("white")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    ax.set_title(
        f"{label}  ·  {count} Reddit posts",
        fontsize=24, fontweight="bold", color="#1a3a5c", pad=18
    )
    plt.tight_layout()

    fname = f"wordcloud_topic{tid:02d}_{label.lower().replace(' ', '_').replace('&','and').replace('(','').replace(')','').replace(',','')}.png"
    plt.savefig(OUT_DIR / fname, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"  Saved: {fname}")

print("\nDone. Files in data/topics/")
