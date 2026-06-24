import TopicRow from './TopicRow'

export default function TopicTable({ topics, activeTopic, onSelect }) {
  return (
    <table className="topic-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Topic · Keywords</th>
          <th>Posts</th>
        </tr>
      </thead>
      <tbody>
        {topics.map((t, i) => (
          <TopicRow
            key={t.id}
            topic={t}
            index={i + 1}
            isActive={activeTopic?.id === t.id}
            onSelect={() => onSelect(t)}
          />
        ))}
      </tbody>
    </table>
  )
}
