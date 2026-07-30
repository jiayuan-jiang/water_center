"""
Pilot: zero-shot NLI stance classification as a cheaper (local model, no
per-call LLM cost) alternative to sentiment-ratio for controversy detection.
Tests whether "supports vs opposes {topic}" stance splits track real
controversy better than positive/negative sentiment splits did.

Validation set: the 8 topics manually LLM-rated for genuine controversy in
this conversation (see spec/controversy-score.md). Compares stance-based
balance ratio against those ratings, alongside the two existing metrics.

Usage:
    python stance_pilot.py
"""

import pandas as pd
from transformers import pipeline

TOPICS = {
    32: "Nestle water privatization",
    27: "boating and water safety accidents",
    0: "the Great Lakes in general",
    6: "Great Lakes water temperature",
    10: "data centers and AI water consumption",
    15: "offshore wind energy on the Great Lakes",
    24: "kayaking and boating",
    26: "Lake Ontario and Toronto area geography",
}
LLM_RATINGS = {32: 0.30, 27: 0.85, 0: 0.10, 6: 0.10, 10: 0.60, 15: 0.75, 24: 0.20, 26: 0.15}

docs = pd.read_csv("data/topics/documents_with_topics.csv")
clf = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

rows = []
for tid, label in TOPICS.items():
    sub = docs[docs["topic"] == tid].copy()
    texts = sub["text"].fillna("").tolist()
    hypothesis = "This comment is {} about " + label + "."
    support_pct, oppose_pct = [], []
    print(f"Topic {tid} ({label}): {len(texts)} docs")
    for i in range(0, len(texts), 32):
        batch = texts[i:i + 32]
        results = clf(batch, candidate_labels=["supportive", "critical"],
                       hypothesis_template=hypothesis, multi_label=False)
        if isinstance(results, dict):
            results = [results]
        for r in results:
            top = r["labels"][0]
            (support_pct if top == "supportive" else oppose_pct).append(1)

    n = len(texts)
    supp = len(support_pct) / n * 100
    opp = len(oppose_pct) / n * 100
    largest = max(supp, opp)
    stance_controversy = (min(supp, opp) / largest) if largest > 0 else 0.0
    rows.append({"topic": tid, "label": label, "pct_supportive": round(supp, 1),
                 "pct_critical": round(opp, 1), "stance_controversy": round(stance_controversy, 3),
                 "llm_rating": LLM_RATINGS[tid]})

out = pd.DataFrame(rows)
print()
print(out.to_string(index=False))
print()
print("corr(llm_rating, stance_controversy) Pearson:",
      round(out["llm_rating"].corr(out["stance_controversy"]), 3),
      " Spearman:", round(out["llm_rating"].corr(out["stance_controversy"], method="spearman"), 3))
out.to_csv("data/analysis/stance_pilot.csv", index=False)
