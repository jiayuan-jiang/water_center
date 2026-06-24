export default function CommentCard({ comment: c, platform }) {
  const isBluesky = platform === 'bluesky'

  // Reddit JSON files use `subreddit`; Bluesky uses `source`
  const sourceLabel = isBluesky
    ? 'Bluesky'
    : `r/${c.source || c.subreddit}`

  return (
    <div className="comment">
      <div className="comment-meta">
        <span className={isBluesky ? 'source-bluesky' : 'sub'}>{sourceLabel}</span>
        <span className="score">↑ {c.score}</span>
        <span style={{ marginLeft: '10px' }}>{c.date}</span>
        {c.url && (
          <a
            href={c.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ marginLeft: '10px', color: 'var(--link-blue)', fontSize: '0.75rem' }}
          >
            ↗ source
          </a>
        )}
      </div>
      <div className="comment-text">{c.text}</div>
    </div>
  )
}
