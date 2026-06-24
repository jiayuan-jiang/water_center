export default function PlatformSelect({ onSelect }) {
  return (
    <div className="platform-select">
      <p className="platform-select-prompt">Select a platform to explore topics</p>
      <div className="platform-cards">
        <button className="platform-card" onClick={() => onSelect('reddit')}>
          <div className="platform-card-name">Reddit</div>
          <div className="platform-card-meta">8,441 comments · 34 topics · 2023–2026</div>
        </button>
        <button className="platform-card" onClick={() => onSelect('bluesky')}>
          <div className="platform-card-name">Bluesky</div>
          <div className="platform-card-meta">125,226 posts · 28 topics · 2023–2026</div>
        </button>
      </div>
    </div>
  )
}