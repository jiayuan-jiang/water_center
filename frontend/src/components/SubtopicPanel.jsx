import { useRef } from 'react'

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
              title={`Jump to comment ${match[1]}`}
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

export default function SubtopicPanel({ subtopics, active, onSelect, onCiteClick }) {
  return (
    <div className="subtopic-section">
      <div className="section-header">Sub-topics</div>
      <div className="subtopic-list">
        {subtopics.map(st => (
          <SubtopicCard
            key={st.subtopic_id}
            st={st}
            isActive={active === st.subtopic_id}
            onSelect={onSelect}
            onCiteClick={onCiteClick}
          />
        ))}
      </div>
    </div>
  )
}

function SubtopicCard({ st, isActive, onSelect, onCiteClick }) {
  return (
    <div className={`subtopic-card${isActive ? ' subtopic-card--active' : ''}`}>
      <div className="subtopic-card-header">
        <span className="subtopic-label">{st.label}</span>
        {st.attitude && (
          <span className="attitude-badge">{st.attitude}</span>
        )}
      </div>

      {st.summary && (
        <p className="subtopic-summary">
          <SummaryWithLinks text={st.summary} onCiteClick={onCiteClick} />
        </p>
      )}

      {st.key_quotes && st.key_quotes.length > 0 && (
        <div className="subtopic-quotes">
          {st.key_quotes.map(q => (
            <blockquote key={q.id} className="subtopic-quote">
              <span className="quote-text">"{q.quote}"</span>
              <button
                className="cite-link quote-cite"
                onClick={() => onCiteClick(q.id)}
                title={`Jump to comment ${q.id}`}
              >
                — {q.id}↗
              </button>
            </blockquote>
          ))}
        </div>
      )}

      <button
        className={`subtopic-filter-btn${isActive ? ' subtopic-filter-btn--active' : ''}`}
        onClick={() => onSelect(st.subtopic_id)}
      >
        {isActive
          ? `Showing ${st.doc_count} comments — click to clear`
          : `Show ${st.doc_count} comments in this sub-topic`}
      </button>
    </div>
  )
}
