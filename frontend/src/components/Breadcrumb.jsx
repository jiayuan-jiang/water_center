const PLATFORM_LABEL = { reddit: 'Reddit', bluesky: 'Bluesky' }

export default function Breadcrumb({ platform, topic, onPlatform, onTopicList }) {
  return (
    <nav className="breadcrumb">
      <span className="breadcrumb-link" onClick={onPlatform}>Platforms</span>
      <span className="breadcrumb-sep">›</span>
      {topic ? (
        <>
          <span className="breadcrumb-link" onClick={onTopicList}>{PLATFORM_LABEL[platform]}</span>
          <span className="breadcrumb-sep">›</span>
          <span className="breadcrumb-current">{topic.label}</span>
        </>
      ) : (
        <span className="breadcrumb-current">{PLATFORM_LABEL[platform]}</span>
      )}
    </nav>
  )
}