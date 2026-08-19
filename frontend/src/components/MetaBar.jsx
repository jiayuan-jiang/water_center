export default function MetaBar({ topics, generated, platform }) {
  if (!topics.length) return <p className="meta-bar">Loading topics…</p>
  const unit = platform === 'reddit' ? 'comments' : 'posts'
  return (
    <p className="meta-bar">
      {topics.length} topics · generated {generated} · click a row to view {unit}
    </p>
  )
}