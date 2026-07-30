import { useEffect, useMemo, useRef, useState } from 'react'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from 'd3-force'

const WIDTH = 900
const HEIGHT = 620
const TICKS = 300

function radiusScale(count, maxCount) {
  const r = 5 + 21 * Math.sqrt(count / maxCount)
  return Math.max(5, Math.min(26, r))
}

function edgeOpacity(weight, threshold) {
  const span = Math.max(1 - threshold, 0.01)
  return 0.08 + 0.55 * ((weight - threshold) / span)
}

function useLayout(nodes, edges) {
  return useMemo(() => {
    if (!nodes.length) return { laidOutNodes: [], laidOutEdges: [] }

    const simNodes = nodes.map(n => ({ ...n }))
    const idIndex = new Map(simNodes.map((n, i) => [n.id, i]))
    const simEdges = edges
      .filter(e => idIndex.has(e.source) && idIndex.has(e.target))
      .map(e => ({ ...e }))

    const chargeStrength = simNodes.length > 150 ? -55 : -140
    const linkDistance = simNodes.length > 150 ? 40 : 90

    const sim = forceSimulation(simNodes)
      .force('link', forceLink(simEdges).id(d => d.id)
        .distance(linkDistance)
        .strength(l => 0.15 + 0.5 * (l.weight - 0.5)))
      .force('charge', forceManyBody().strength(chargeStrength))
      .force('center', forceCenter(WIDTH / 2, HEIGHT / 2))
      .force('collide', forceCollide().radius(d => radiusScale(d.count, maxCountOf(simNodes)) + 2))
      .stop()

    for (let i = 0; i < TICKS; i++) sim.tick()

    return { laidOutNodes: simNodes, laidOutEdges: simEdges }
  }, [nodes, edges])
}

function maxCountOf(nodes) {
  return Math.max(1, ...nodes.map(n => n.count))
}

export default function NetworkGraph({ data, onSelectNode }) {
  const [threshold, setThreshold] = useState(data.threshold)
  const [hovered, setHovered] = useState(null)
  const [selected, setSelected] = useState(null)
  const [view, setView] = useState({ x: 0, y: 0, scale: 1 })
  const dragRef = useRef(null)
  const svgRef = useRef(null)

  useEffect(() => {
    setThreshold(data.threshold)
    setSelected(null)
    setView({ x: 0, y: 0, scale: 1 })
  }, [data])

  const { laidOutNodes, laidOutEdges } = useLayout(data.nodes, data.edges)
  const maxCount = useMemo(() => maxCountOf(laidOutNodes), [laidOutNodes])
  const nodeById = useMemo(() => new Map(laidOutNodes.map(n => [n.id, n])), [laidOutNodes])

  const visibleEdges = useMemo(
    () => laidOutEdges.filter(e => e.weight >= threshold),
    [laidOutEdges, threshold]
  )

  const neighborIds = useMemo(() => {
    if (!selected) return null
    const s = new Set([selected.id])
    for (const e of visibleEdges) {
      const src = e.source.id ?? e.source
      const tgt = e.target.id ?? e.target
      if (src === selected.id) s.add(tgt)
      if (tgt === selected.id) s.add(src)
    }
    return s
  }, [selected, visibleEdges])

  const selectedNeighbors = useMemo(() => {
    if (!selected) return []
    return visibleEdges
      .filter(e => (e.source.id ?? e.source) === selected.id || (e.target.id ?? e.target) === selected.id)
      .map(e => {
        const src = e.source.id ?? e.source
        const tgt = e.target.id ?? e.target
        const otherId = src === selected.id ? tgt : src
        return { node: nodeById.get(otherId), weight: e.weight }
      })
      .filter(x => x.node)
      .sort((a, b) => b.weight - a.weight)
  }, [selected, visibleEdges, nodeById])

  const handleWheel = e => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.9 : 1.1
    setView(v => ({ ...v, scale: Math.max(0.4, Math.min(3, v.scale * delta)) }))
  }

  const handlePointerDown = e => {
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: view.x, origY: view.y }
  }
  const handlePointerMove = e => {
    if (!dragRef.current) return
    const { startX, startY, origX, origY } = dragRef.current
    setView(v => ({ ...v, x: origX + (e.clientX - startX), y: origY + (e.clientY - startY) }))
  }
  const handlePointerUp = () => { dragRef.current = null }

  if (!laidOutNodes.length) {
    return <p className="loading-state">No similarity data available for this set yet.</p>
  }

  return (
    <div className="network-wrap">
      <div className="network-toolbar">
        <label className="network-slider-label">
          Min similarity ≥ {threshold.toFixed(2)}
          <input
            type="range"
            min={data.threshold}
            max="0.95"
            step="0.01"
            value={threshold}
            onChange={e => setThreshold(parseFloat(e.target.value))}
          />
        </label>
        <span className="network-stat">
          {laidOutNodes.length} nodes · {visibleEdges.length} edges shown
        </span>
        <span className="network-hint">scroll to zoom · drag to pan</span>
      </div>

      <div className="network-canvas">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="network-svg"
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
        >
          <g transform={`translate(${view.x} ${view.y}) scale(${view.scale})`}>
            <g className="network-edges">
              {visibleEdges.map((e, i) => {
                const src = typeof e.source === 'object' ? e.source : nodeById.get(e.source)
                const tgt = typeof e.target === 'object' ? e.target : nodeById.get(e.target)
                if (!src || !tgt) return null
                const dim = selected && !(neighborIds.has(src.id) && neighborIds.has(tgt.id))
                return (
                  <line
                    key={i}
                    x1={src.x} y1={src.y} x2={tgt.x} y2={tgt.y}
                    stroke="var(--um-blue)"
                    strokeOpacity={dim ? 0.03 : edgeOpacity(e.weight, threshold)}
                    strokeWidth={1}
                  />
                )
              })}
            </g>
            <g className="network-nodes">
              {laidOutNodes.map(n => {
                const dim = selected && !neighborIds.has(n.id)
                const isSelected = selected?.id === n.id
                return (
                  <g
                    key={n.id}
                    transform={`translate(${n.x} ${n.y})`}
                    onMouseEnter={() => setHovered(n)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => {
                      setSelected(n)
                      onSelectNode?.(n)
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle
                      r={radiusScale(n.count, maxCount)}
                      fill={isSelected ? 'var(--um-maize)' : 'var(--um-blue)'}
                      fillOpacity={dim ? 0.15 : 0.85}
                      stroke={isSelected ? 'var(--um-blue)' : 'none'}
                      strokeWidth={isSelected ? 2 : 0}
                    />
                  </g>
                )
              })}
            </g>
          </g>
        </svg>

        {hovered && (
          <div className="network-tooltip">
            <div className="network-tooltip-label">{hovered.label}</div>
            <div className="network-tooltip-meta">{hovered.count} docs</div>
            <div className="keywords">
              {hovered.keywords.slice(0, 5).map(k => <span key={k} className="kw">{k}</span>)}
            </div>
          </div>
        )}
      </div>

      {selected && (
        <div className="network-side-panel">
          <div className="network-side-header">
            <span className="label">{selected.label}</span>
            <button className="network-close-btn" onClick={() => setSelected(null)}>×</button>
          </div>
          <div className="network-side-meta">{selected.count} docs</div>
          <div className="keywords">
            {selected.keywords.map(k => <span key={k} className="kw">{k}</span>)}
          </div>
          <div className="network-side-neighbors">
            <div className="section-header">Related ({selectedNeighbors.length})</div>
            {selectedNeighbors.length === 0 && (
              <p className="network-no-edges">No connections at this similarity threshold.</p>
            )}
            {selectedNeighbors.map(({ node, weight }) => (
              <div key={node.id} className="network-neighbor-row" onClick={() => setSelected(node)}>
                <span className="network-neighbor-label">{node.label}</span>
                <span className="network-neighbor-weight">{weight.toFixed(2)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
