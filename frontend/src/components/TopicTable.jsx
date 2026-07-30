import { useMemo, useState } from 'react'
import TopicRow from './TopicRow'
import { SteepFilterBar, filterBySteep } from '../steep'

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
  const [steepActive, setSteepActive] = useState(new Set())

  const handleSort = field => {
    setSort(prev =>
      prev.field === field
        ? { field, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
        : { field, dir: 'desc' }
    )
  }

  const toggleSteep = cat => {
    setSteepActive(prev => {
      if (cat === null) return new Set()
      const next = new Set(prev)
      next.has(cat) ? next.delete(cat) : next.add(cat)
      return next
    })
  }

  const filtered = useMemo(
    () => filterBySteep(topics, t => t.steep, steepActive),
    [topics, steepActive]
  )

  const sorted = useMemo(() => {
    if (sort.field !== 'controversy') return filtered
    const withOrder = filtered.map((t, i) => ({ t, i }))
    withOrder.sort((a, b) => {
      const diff = (a.t.controversy?.score ?? 0) - (b.t.controversy?.score ?? 0)
      if (diff !== 0) return sort.dir === 'asc' ? diff : -diff
      return a.i - b.i
    })
    return withOrder.map(({ t }) => t)
  }, [filtered, sort])

  return (
    <>
      <SteepFilterBar items={topics} getSteep={t => t.steep} active={steepActive} onToggle={toggleSteep} />
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
    </>
  )
}
