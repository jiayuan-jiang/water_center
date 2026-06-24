export default function TopicRow({ topic, index, isActive, onSelect }) {
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
      <td>{topic.count}</td>
    </tr>
  )
}
