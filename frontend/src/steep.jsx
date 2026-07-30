// STEEP category colors — validated against dataviz color-formula (adjacent-pairs
// safe: CVD floor and normal-vision floor both pass for badges/chips/line charts).
// Note: these 5 hues do NOT clear the stricter all-pairs check needed for a dense
// scatter/network view, so NetworkGraph uses this only as a secondary accent
// (ring), never the sole identity channel — see NetworkGraph.jsx.
export const STEEP_CATEGORIES = ['Social', 'Technological', 'Economic', 'Environmental', 'Political']

export const STEEP_COLORS = {
  Social: '#2a78d6',
  Technological: '#eb6834',
  Economic: '#1baf7a',
  Environmental: '#eda100',
  Political: '#e87ba4',
}

export function SteepBadges({ steep }) {
  if (!steep?.tags?.length) return null
  return (
    <span className="steep-badges" title={steep.rationale || undefined}>
      {steep.tags.map(tag => (
        <span key={tag} className="steep-badge">
          <span className="steep-dot" style={{ background: STEEP_COLORS[tag] }} />
          {tag}
        </span>
      ))}
    </span>
  )
}

export function SteepFilterBar({ items, getSteep, active, onToggle }) {
  const countByCategory = Object.fromEntries(STEEP_CATEGORIES.map(c => [c, 0]))
  for (const item of items) {
    for (const tag of getSteep(item)?.tags ?? []) {
      if (countByCategory[tag] !== undefined) countByCategory[tag] += 1
    }
  }
  return (
    <div className="steep-filter-bar">
      {STEEP_CATEGORIES.map(cat => {
        const count = countByCategory[cat]
        const isActive = active.has(cat)
        return (
          <button
            key={cat}
            className={`steep-chip${isActive ? ' steep-chip--active' : ''}`}
            style={isActive ? { borderColor: STEEP_COLORS[cat], background: `${STEEP_COLORS[cat]}1a` } : undefined}
            onClick={() => onToggle(cat)}
            disabled={count === 0}
          >
            <span className="steep-dot" style={{ background: STEEP_COLORS[cat] }} />
            {cat} <span className="steep-chip-count">{count}</span>
          </button>
        )
      })}
      {active.size > 0 && (
        <button className="steep-chip steep-chip-clear" onClick={() => onToggle(null)}>Clear</button>
      )}
    </div>
  )
}

export function filterBySteep(items, getSteep, active) {
  if (active.size === 0) return items
  return items.filter(item => {
    const tags = getSteep(item)?.tags ?? []
    return tags.some(t => active.has(t))
  })
}
