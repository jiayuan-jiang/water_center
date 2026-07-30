import { useMemo, useState } from 'react'

function WaterBadge({ value }) {
  if (value === true) return <span className="water-badge water-badge--yes">water ✓</span>
  if (value === false) return <span className="water-badge water-badge--no">off-topic ✗</span>
  return null
}

const SORT_FIELDS = {
  docs: c => c.n_docs,
  novelty: c => c.novelty,
  recency: c => c.recency,
}

function SortHeader({ label, field, sort, onSort }) {
  const active = sort.field === field
  return (
    <th className="sortable-th" onClick={() => onSort(field)}>
      {label}
      <span className={`sort-arrow${active ? ' sort-arrow--active' : ''}`}>
        {active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}
      </span>
    </th>
  )
}

export default function OutlierTable({ clusters, onSelect }) {
  const [sort, setSort] = useState({ field: null, dir: 'desc' })

  const handleSort = field => {
    setSort(prev =>
      prev.field === field
        ? { field, dir: prev.dir === 'desc' ? 'asc' : 'desc' }
        : { field, dir: 'desc' }
    )
  }

  const sorted = useMemo(() => {
    if (!sort.field) return clusters
    const getValue = SORT_FIELDS[sort.field]
    const withOrder = clusters.map((c, i) => ({ c, i }))
    withOrder.sort((a, b) => {
      const diff = getValue(a.c) - getValue(b.c)
      if (diff !== 0) return sort.dir === 'asc' ? diff : -diff
      return a.i - b.i
    })
    return withOrder.map(({ c }) => c)
  }, [clusters, sort])

  return (
    <table className="topic-table outlier-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Candidate · Keywords</th>
          <SortHeader label="Docs" field="docs" sort={sort} onSort={handleSort} />
          <SortHeader label="Novelty" field="novelty" sort={sort} onSort={handleSort} />
          <SortHeader label="Recency" field="recency" sort={sort} onSort={handleSort} />
          <th>Active</th>
        </tr>
      </thead>
      <tbody>
        {sorted.map((c, i) => (
          <tr key={c.id} onClick={() => onSelect(c)}>
            <td>{i + 1}</td>
            <td>
              <span className="label">{c.label}</span>
              <WaterBadge value={c.water_related} />
              <div className="keywords">
                {c.keywords.slice(0, 6).map(k => <span key={k} className="kw">{k}</span>)}
              </div>
            </td>
            <td className="num-cell">{c.n_docs}</td>
            <td className="num-cell">{c.novelty.toFixed(2)}</td>
            <td className="num-cell">{Math.round(c.recency * 100)}%</td>
            <td className="range-cell">{c.first_month} → {c.last_month}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
