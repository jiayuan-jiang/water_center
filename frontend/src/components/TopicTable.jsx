import { useMemo, useState } from 'react'
import TopicRow from './TopicRow'

function SortHeader({ label, field, sort, onSort }) {
  const active = sort.field === field
  return (
    <th className="sortable-th" onClick={() => onSort(field)}>
      <span className="th-label">
        {label}
        <span className={`sort-arrow${active ? ' sort-arrow--active' : ''}`}>
          {active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}
        </span>
      </span>
    </th>
  )
}

export default function TopicTable({ topics, activeTopic, onSelect }) {
  const [sort, setSort] = useState({ field: null, dir: 'desc' })

  const handleSort = field => {
    setSort(prev =>
      prev.field === field
        ? { field, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
        : { field, dir: 'desc' }
    )
  }

  const sorted = useMemo(() => {
    if (sort.field !== 'controversy') return topics
    const withOrder = topics.map((t, i) => ({ t, i }))
    withOrder.sort((a, b) => {
      const diff = (a.t.controversy?.score ?? 0) - (b.t.controversy?.score ?? 0)
      if (diff !== 0) return sort.dir === 'asc' ? diff : -diff
      return a.i - b.i
    })
    return withOrder.map(({ t }) => t)
  }, [topics, sort])

  return (
    <table className="topic-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Topic · Keywords</th>
          <th>Mood</th>
          <th>Posts</th>
          <SortHeader label="Controversy" field="controversy" sort={sort} onSort={handleSort} />
        </tr>
      </thead>
      <tbody>
        {sorted.map((t, i) => (
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
