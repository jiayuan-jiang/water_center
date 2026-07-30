import { useState } from 'react'

// Fixed category order + color assignment — never reordered or recycled,
// so "fear" is always violet, "joy" always yellow, etc. across every chart.
// Colors are the validated categorical palette (see dataviz skill); neutral
// is deliberately left an unsaturated gray, not a categorical slot — it's
// "no strong emotion", the quiet majority in most topics, not a competing series.
const EMOTION_ORDER = ['neutral', 'joy', 'surprise', 'sadness', 'disgust', 'fear', 'anger']
const EMOTION_COLOR = {
  neutral:  '#b9b9b4',
  joy:      '#eda100',
  surprise: '#1baf7a',
  sadness:  '#2a78d6',
  disgust:  '#008300',
  fear:     '#4a3aa7',
  anger:    '#e34948',
}
const EMOTION_EMOJI = {
  neutral: '😐', joy: '😊', surprise: '😲', sadness: '😢', disgust: '🤢', fear: '😨', anger: '😠',
}

const R = 58
const CX = 64
const CY = 64
const GAP_DEG = 1.2 // thin surface-color gap between slices

function arcPath(startDeg, endDeg) {
  const s = startDeg - GAP_DEG / 2
  const e = endDeg + GAP_DEG / 2
  if (e - s <= GAP_DEG) return null
  const toXY = deg => {
    const rad = ((deg - 90) * Math.PI) / 180
    return [CX + R * Math.cos(rad), CY + R * Math.sin(rad)]
  }
  const [x1, y1] = toXY(s + GAP_DEG / 2)
  const [x2, y2] = toXY(e - GAP_DEG / 2)
  const large = e - s > 180 ? 1 : 0
  return `M ${CX} ${CY} L ${x1} ${y1} A ${R} ${R} 0 ${large} 1 ${x2} ${y2} Z`
}

export default function EmotionPieChart({ pct, title }) {
  const [hovered, setHovered] = useState(null)
  if (!pct) return null

  const slices = EMOTION_ORDER
    .map(key => ({ key, value: pct[key] ?? 0 }))
    .filter(s => s.value > 0)
  const total = slices.reduce((a, s) => a + s.value, 0)
  if (total <= 0) return null

  let cursor = 0
  const withAngles = slices.map(s => {
    const start = (cursor / total) * 360
    cursor += s.value
    const end = (cursor / total) * 360
    return { ...s, start, end }
  })

  const hoveredSlice = withAngles.find(s => s.key === hovered)

  return (
    <div className="emotion-pie">
      {title && <div className="section-header">{title}</div>}
      <div className="emotion-pie-body">
        <svg viewBox="0 0 128 128" width="128" height="128" className="emotion-pie-svg">
          {withAngles.map(s => {
            const d = arcPath(s.start, s.end)
            if (!d) return null
            const mid = (s.start + s.end) / 2
            const labelRad = ((mid - 90) * Math.PI) / 180
            const showLabel = s.value >= 8
            const lx = CX + R * 0.68 * Math.cos(labelRad)
            const ly = CY + R * 0.68 * Math.sin(labelRad)
            return (
              <g key={s.key}
                 onMouseEnter={() => setHovered(s.key)}
                 onMouseLeave={() => setHovered(null)}
                 style={{ cursor: 'default' }}>
                <path
                  d={d}
                  fill={EMOTION_COLOR[s.key]}
                  stroke={hovered === s.key ? '#fff' : 'none'}
                  strokeWidth={hovered === s.key ? 2 : 0}
                  opacity={hovered && hovered !== s.key ? 0.55 : 1}
                />
                <title>{`${s.key} ${s.value.toFixed(1)}%`}</title>
                {showLabel && (
                  <text
                    x={lx} y={ly}
                    fontSize={10} fill="#fff" fontFamily="Courier New, monospace"
                    textAnchor="middle" dominantBaseline="middle"
                    style={{ pointerEvents: 'none' }}
                  >
                    {Math.round(s.value)}%
                  </text>
                )}
              </g>
            )
          })}
        </svg>
        <div className="emotion-pie-legend">
          {withAngles.map(s => (
            <div
              key={s.key}
              className={`emotion-pie-legend-row${hovered === s.key ? ' emotion-pie-legend-row--hover' : ''}`}
              onMouseEnter={() => setHovered(s.key)}
              onMouseLeave={() => setHovered(null)}
            >
              <span className="emotion-pie-swatch" style={{ background: EMOTION_COLOR[s.key] }} />
              <span className="emotion-pie-label">{EMOTION_EMOJI[s.key]} {s.key}</span>
              <span className="emotion-pie-pct">{s.value.toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
      {hoveredSlice && (
        <div className="emotion-pie-tooltip">
          {EMOTION_EMOJI[hoveredSlice.key]} <strong>{hoveredSlice.value.toFixed(1)}%</strong> {hoveredSlice.key}
        </div>
      )}
    </div>
  )
}
