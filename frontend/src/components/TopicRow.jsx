import { EmotionBadge } from '../emotions'

const VERDICT_LABELS = {
  genuine_debate: 'Genuine debate',
  one_sided_consensus: 'One-sided',
  heterogeneous_not_contentious: 'Heterogeneous',
  insufficient_data: 'Insufficient data',
}

export default function TopicRow({ topic, index, isActive, onSelect }) {
  const controversy = topic.controversy
  return (
    <tr className={isActive ? 'active' : undefined} onClick={onSelect}>
      <td>{index}</td>
      <td>
        <div className="label">{topic.label}</div>
        <div className="keywords">
          {topic.keywords.map(k => (
            <span key={k} className="kw">{k}</span>
          ))}
        </div>
      </td>
      <td><EmotionBadge emotion={topic.emotion?.dominant} /></td>
      <td>{topic.count}</td>
      <td className="num-cell">
        {controversy && (
          <>
            {controversy.score.toFixed(2)}
            <div className="verdict-tag">{VERDICT_LABELS[controversy.verdict] ?? controversy.verdict}</div>
          </>
        )}
      </td>
    </tr>
  )
}
