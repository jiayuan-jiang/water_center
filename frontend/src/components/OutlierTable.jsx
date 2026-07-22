function WaterBadge({ value }) {
  if (value === true) return <span className="water-badge water-badge--yes">water ✓</span>
  if (value === false) return <span className="water-badge water-badge--no">off-topic ✗</span>
  return null
}

export default function OutlierTable({ clusters, onSelect }) {
  return (
    <table className="topic-table outlier-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Candidate · Keywords</th>
          <th>Docs</th>
          <th>Novelty</th>
          <th>Recency</th>
          <th>Active</th>
        </tr>
      </thead>
      <tbody>
        {clusters.map((c, i) => (
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
