const SVG_W = 860
const INNER_H = 150
const PAD = { top: 18, right: 10, bottom: 28, left: 42 }
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

export default function TrendChart({ trendData, topicId }) {
  if (!trendData) return null

  const topicTrend = trendData.topics.find(t => t.topic_id === topicId)
  if (!topicTrend) return null

  const { months } = trendData
  const { count } = topicTrend.monthly
  const smooth = movingAvg(count, 2)

  const maxY = Math.max(...count, 0.001)
  const barW = CHART_W / months.length
  const { start, end } = trendData.meta.date_range

  const yTicks = [0, 0.5, 1]

  return (
    <div className="trend-wrap">
      <div className="trend-section-header">
        Monthly document count
        <span className="trend-date-range">{start} – {end}</span>
        <span className="trend-loess-label">&#8212; 5-month moving avg</span>
      </div>
      <div className="trend-single-panel">
        <svg
          viewBox={`0 0 ${SVG_W} ${SVG_H}`}
          style={{ width: '100%', display: 'block', overflow: 'visible' }}
        >
          {/* Grid lines + Y labels */}
          {yTicks.map(frac => {
            const val = maxY * frac
            const y = PAD.top + INNER_H * (1 - frac)
            return (
              <g key={frac}>
                <line
                  x1={PAD.left} x2={PAD.left + CHART_W}
                  y1={y} y2={y}
                  stroke={frac === 0 ? '#bbb' : '#e8e8e8'}
                  strokeWidth={1}
                />
                <text
                  x={PAD.left - 5} y={y + 3}
                  fontSize={9} fill="#888"
                  textAnchor="end" fontFamily="Courier New, monospace"
                >
                  {Math.round(val)}
                </text>
              </g>
            )
          })}

          {/* Bars */}
          {count.map((v, i) => {
            const h = (v / maxY) * INNER_H
            if (h <= 0) return null
            return (
              <rect
                key={i}
                x={PAD.left + i * barW + 1}
                y={PAD.top + INNER_H - h}
                width={Math.max(barW - 2, 1)}
                height={h}
                fill="#00274c"
                opacity={0.85}
              />
            )
          })}

          {/* Smooth line */}
          <polyline
            points={smooth.map((v, i) => {
              const x = PAD.left + i * barW + barW / 2
              const y = PAD.top + INNER_H - (v / maxY) * INNER_H
              return `${x},${y}`
            }).join(' ')}
            fill="none"
            stroke="#c0392b"
            strokeWidth={2.5}
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* X-axis year labels */}
          {months.map((m, i) => {
            if (!m.endsWith('-01') && i !== 0) return null
            const x = PAD.left + i * barW + barW / 2
            return (
              <text
                key={i}
                x={x} y={PAD.top + INNER_H + 18}
                fontSize={9} fill="#666"
                textAnchor="middle" fontFamily="Courier New, monospace"
              >
                {m.slice(0, 4)}
              </text>
            )
          })}
        </svg>
      </div>
    </div>
  )
}