import { useState, useEffect } from 'react'
import CommentCard from './CommentCard'

// Render summary text, turning [id] tokens into clickable buttons
function SummaryWithLinks({ text, onCiteClick }) {
  if (!text) return null
  const parts = text.split(/(\[[a-z0-9]+\])/g)
  return (
    <span>
      {parts.map((part, i) => {
        const match = part.match(/^\[([a-z0-9]+)\]$/)
        if (match) {
          return (
            <button
              key={i}
              className="cite-link"
              onClick={() => onCiteClick(match[1])}
              title={`Jump to document ${match[1]}`}
            >
              [{match[1]}↗]
            </button>
          )
        }
        return part
      })}
    </span>
  )
}

// Fill the gap months between first and last so the bar strip is honest
function monthRange(counts) {
  const keys = Object.keys(counts).sort()
  if (!keys.length) return []
  const out = []
  let [y, m] = keys[0].split('-').map(Number)
  const last = keys[keys.length - 1]
  let cur = keys[0]
  while (cur <= last) {
    out.push([cur, counts[cur] ?? 0])
    m += 1
    if (m > 12) { m = 1; y += 1 }
    cur = `${y}-${String(m).padStart(2, '0')}`
  }
  return out
}

function MonthlyBars({ counts }) {
  const months = monthRange(counts)
  if (months.length < 2) return null
  const max = Math.max(...months.map(([, n]) => n))
  return (
    <div className="month-bars-wrap">
      <div className="month-bars">
        {months.map(([month, n]) => (
          <div
            key={month}
            className="month-bar"
            style={{ height: `${n === 0 ? 2 : 4 + (n / max) * 36}px` }}
            title={`${month}: ${n}`}
          />
        ))}
      </div>
      <div className="month-bars-range">
        <span>{months[0][0]}</span>
        <span>{months[months.length - 1][0]}</span>
      </div>
    </div>
  )
}

export default function OutlierDetail({ cluster, platform }) {
  const [docs, setDocs] = useState(null)

  useEffect(() => {
    setDocs(null)
    fetch(`data/outliers/${platform}/c${cluster.id}.json`)
      .then(r => r.json())
      .then(d => setDocs(d.docs))
      .catch(() => setDocs([]))
  }, [cluster.id, platform])

  const handleCiteClick = (id) => {
    const el = document.getElementById(`comment-${id}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }

  const citedIds = new Set(cluster.key_quotes?.map(q => q.id) ?? [])
  const unit = platform === 'bluesky' ? 'posts' : 'comments'

  return (
    <div id="detail">
      <div id="detail-header">
        <div>
          <h2>{cluster.label}</h2>
          <div className="detail-keywords">
            {cluster.keywords.map(k => <span key={k} className="kw">{k}</span>)}
          </div>
        </div>
        <span className="detail-count">
          {cluster.n_docs} {unit} · unreviewed candidate
        </span>
      </div>

      <div className="outlier-scores">
        <span className="outlier-score">relevance {cluster.relevance.toFixed(2)}</span>
        <span className="outlier-score">novelty {cluster.novelty.toFixed(2)}</span>
        <span className="outlier-score">recency {Math.round(cluster.recency * 100)}%</span>
        <span className="outlier-score">first seen {cluster.first_month}</span>
        {cluster.water_related === false && (
          <span className="water-badge water-badge--no">flagged off-topic by LLM</span>
        )}
      </div>

      <MonthlyBars counts={cluster.monthly_counts} />

      {cluster.summary && (
        <div className="outlier-summary">
          <div className="section-header">Grounded summary</div>
          <p className="subtopic-summary outlier-summary-text">
            <SummaryWithLinks text={cluster.summary} onCiteClick={handleCiteClick} />
          </p>
          {cluster.key_quotes?.length > 0 && (
            <div className="subtopic-quotes outlier-quotes">
              {cluster.key_quotes.map(q => (
                <blockquote key={q.id} className="subtopic-quote">
                  <span className="quote-text">"{q.quote}"</span>
                  <button
                    className="cite-link quote-cite"
                    onClick={() => handleCiteClick(q.id)}
                    title={`Jump to document ${q.id}`}
                  >
                    — {q.id}↗
                  </button>
                </blockquote>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="comment-section-header">
        <span className="comment-section-title">
          All {unit} in this cluster
        </span>
      </div>

      <div id="comment-list">
        {docs === null
          ? <div className="loading-state">Loading…</div>
          : docs.map(c => (
              <CommentCard
                key={c.id}
                comment={c}
                platform={platform}
                highlighted={citedIds.has(c.id)}
              />
            ))
        }
      </div>
    </div>
  )
}
