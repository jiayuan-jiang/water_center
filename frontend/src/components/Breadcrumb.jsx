const PLATFORM_LABEL = { reddit: 'Reddit', bluesky: 'Bluesky' }
const MODE_LABEL = { topics: 'Topics', outliers: 'Outlier Signals' }

export default function Breadcrumb({ platform, mode, current, onPlatform, onMode, onList }) {
  return (
    <nav className="breadcrumb">
      <span className="breadcrumb-link" onClick={onPlatform}>Platforms</span>
      <span className="breadcrumb-sep">›</span>
      {mode ? (
        <>
          <span className="breadcrumb-link" onClick={onMode}>{PLATFORM_LABEL[platform]}</span>
          <span className="breadcrumb-sep">›</span>
          {current ? (
            <>
              <span className="breadcrumb-link" onClick={onList}>{MODE_LABEL[mode]}</span>
              <span className="breadcrumb-sep">›</span>
              <span className="breadcrumb-current">{current}</span>
            </>
          ) : (
            <span className="breadcrumb-current">{MODE_LABEL[mode]}</span>
          )}
        </>
      ) : (
        <span className="breadcrumb-current">{PLATFORM_LABEL[platform]}</span>
      )}
    </nav>
  )
}
