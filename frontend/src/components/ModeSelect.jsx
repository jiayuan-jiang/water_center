import { useState, useEffect } from 'react'
import SteepTrendMini from './SteepTrendMini'

const PLATFORM_LABEL = { reddit: 'Reddit', bluesky: 'Bluesky', mastodon: 'Mastodon' }

export default function ModeSelect({ platform, onSelect }) {
  const [topicCount, setTopicCount] = useState(null)
  const [outlierMeta, setOutlierMeta] = useState(null)

  useEffect(() => {
    setTopicCount(null)
    setOutlierMeta(null)
    const topicsUrl = platform === 'reddit' ? 'data/topics.json' : `data/${platform}/topics.json`
    fetch(topicsUrl)
      .then(r => r.json())
      .then(json => setTopicCount(json.topics.length))
      .catch(() => {})
    fetch(`data/outliers/${platform}/clusters.json`)
      .then(r => r.ok ? r.json() : null)
      .then(setOutlierMeta)
      .catch(() => {})
  }, [platform])

  return (
    <div className="platform-select">
      <p className="platform-select-prompt">
        {PLATFORM_LABEL[platform]} — choose a view
      </p>
      <div className="platform-cards">
        <button className="platform-card" onClick={() => onSelect('topics')}>
          <div className="platform-card-name">Topics</div>
          <div className="platform-card-meta">
            {topicCount ?? '…'} labeled topics · curated
          </div>
        </button>
        <button className="platform-card" onClick={() => onSelect('outliers')}>
          <div className="platform-card-name">Outlier Signals</div>
          <div className="platform-card-meta">
            {outlierMeta ? `${outlierMeta.n_passing} micro-clusters` : '…'} · unreviewed candidates
          </div>
        </button>
      </div>
      <p className="mode-select-note">
        Outlier signals are small clusters recovered from documents the main topic
        model could not assign — potential emerging issues, not yet audited.
      </p>
      <SteepTrendMini platform={platform} />
    </div>
  )
}
