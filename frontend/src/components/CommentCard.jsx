import { EmotionBadge } from '../emotions'

export default function CommentCard({ comment: c, platform, highlighted }) {
  const isBluesky = platform === 'bluesky'

  const sourceLabel = isBluesky
    ? 'Bluesky'
    : `r/${c.source || c.subreddit}`

  return (
    <div
      id={`comment-${c.id}`}
      className={`comment${highlighted ? ' comment--highlighted' : ''}`}
    >
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
        {c.emotion && <span className="comment-emotion"><EmotionBadge emotion={c.emotion} /></span>}
      </div>
      <div className="comment-text">{c.text}</div>
    </div>
  )
}
