import { useEffect, useMemo, useState } from 'react'
import { STEEP_CATEGORIES, STEEP_COLORS } from '../steep'

const SVG_W = 720
const INNER_H = 130
const PAD = { top: 8, right: 10, bottom: 22, left: 34 }
const CHART_W = SVG_W - PAD.left - PAD.right
const SVG_H = PAD.top + INNER_H + PAD.bottom

function movingAvg(arr, halfWin = 2) {
  return arr.map((_, i) => {
    const lo = Math.max(0, i - halfWin)
    const hi = Math.min(arr.length - 1, i + halfWin)
    const slice = arr.slice(lo, hi + 1)
    return slice.reduce((a, b) => a + b, 0) / slice.length
  })
}

export default function SteepTrendMini({ platform }) {
  const [data, setData] = useState(null)
  const [hoverIdx, setHoverIdx] = useState(null)

  useEffect(() => {
    setData(null)
    fetch(`data/steep_trends/${platform}.json`)
      .then(r => r.ok ? r.json() : null)
      .then(setData)
      .catch(() => setData(null))
  }, [platform])

  const smoothed = useMemo(() => {
    if (!data) return null
    return Object.fromEntries(
      STEEP_CATEGORIES.map(cat => [cat, movingAvg(data.categories[cat].count, 2)])
    )
  }, [data])

  if (!data || !smoothed) return null

  const { months } = data
  const maxY = Math.max(
    1,
    ...STEEP_CATEGORIES.flatMap(cat => smoothed[cat])
  )
  const xStep = CHART_W / (months.length - 1)
  const yFor = v => PAD.top + INNER_H * (1 - v / maxY)
  const xFor = i => PAD.left + i * xStep

  const handleMove = e => {
    const rect = e.currentTarget.getBoundingClientRect()
    const relX = ((e.clientX - rect.left) / rect.width) * SVG_W
    const idx = Math.round((relX - PAD.left) / xStep)
    setHoverIdx(Math.max(0, Math.min(months.length - 1, idx)))
  }

  return (
    <div className="steep-trend-mini">
      <div className="steep-trend-mini-header">
        <span>STEEP category monthly document count (topics + flagged outliers, 5-month smoothed)</span>
      </div>
      <div className="steep-legend steep-trend-mini-legend">
        {STEEP_CATEGORIES.map(cat => (
          <span key={cat} className="steep-legend-item">
            <span className="steep-dot" style={{ background: STEEP_COLORS[cat] }} />
            {cat}
          </span>
        ))}
      </div>
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        style={{ width: '100%', display: 'block', overflow: 'visible' }}
        onMouseMove={handleMove}
        onMouseLeave={() => setHoverIdx(null)}
      >
        {[0, 0.5, 1].map(frac => {
          const y = PAD.top + INNER_H * (1 - frac)
          return (
            <g key={frac}>
              <line x1={PAD.left} x2={PAD.left + CHART_W} y1={y} y2={y}
                    stroke={frac === 0 ? '#bbb' : '#e8e8e8'} strokeWidth={1} />
              <text x={PAD.left - 5} y={y + 3} fontSize={9} fill="#888"
                    textAnchor="end" fontFamily="Courier New, monospace">
                {Math.round(maxY * frac)}
              </text>
            </g>
          )
        })}

        {STEEP_CATEGORIES.map(cat => (
          <polyline
            key={cat}
            points={smoothed[cat].map((v, i) => `${xFor(i)},${yFor(v)}`).join(' ')}
            fill="none"
            stroke={STEEP_COLORS[cat]}
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {hoverIdx !== null && (
          <line x1={xFor(hoverIdx)} x2={xFor(hoverIdx)} y1={PAD.top} y2={PAD.top + INNER_H}
                stroke="#999" strokeWidth={1} strokeDasharray="3,3" />
        )}

        {months.map((m, i) => {
          if (!m.endsWith('-01') && i !== 0) return null
          return (
            <text key={i} x={xFor(i)} y={PAD.top + INNER_H + 15} fontSize={9} fill="#666"
                  textAnchor="middle" fontFamily="Courier New, monospace">
              {m.slice(0, 4)}
            </text>
          )
        })}
      </svg>

      {hoverIdx !== null && (
        <div className="steep-trend-mini-tooltip">
          <span className="steep-trend-mini-tooltip-month">{months[hoverIdx]}</span>
          {STEEP_CATEGORIES.map(cat => (
            <span key={cat} className="steep-trend-mini-tooltip-item">
              <span className="steep-dot" style={{ background: STEEP_COLORS[cat] }} />
              {Math.round(smoothed[cat][hoverIdx])}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
