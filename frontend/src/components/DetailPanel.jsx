import { useState, useEffect } from 'react'
import CommentCard from './CommentCard'

export default function DetailPanel({ topic, platform }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    setData(null)
    const base = platform === 'bluesky' ? 'data/bluesky/topics' : 'data/topics'
    fetch(`${base}/t${topic.id}.json`)
      .then(r => r.json())
      .then(setData)
  }, [topic.id, platform])

  const unit = platform === 'bluesky' ? 'posts' : 'comments'

  return (
    <div id="detail">
      <div id="detail-header">
        <div>
          <h2>{topic.label}</h2>
          <div className="detail-keywords">
            {topic.keywords.map(k => <span key={k} className="kw">{k}</span>)}
          </div>
        </div>
        <span className="detail-count">
          {data ? `${data.comments.length} representative ${unit} · sorted by score` : ''}
        </span>
      </div>
      <div id="comment-list">
        {!data
          ? <div style={{ padding: '18px', color: '#666', fontSize: '0.85rem' }}>Loading…</div>
          : data.comments.map(c => <CommentCard key={c.id} comment={c} platform={platform} />)
        }
      </div>
    </div>
  )
}
