import { useState, useEffect } from 'react'
import Header from './components/Header'
import MetaBar from './components/MetaBar'
import TopicTable from './components/TopicTable'
import DetailPanel from './components/DetailPanel'
import Breadcrumb from './components/Breadcrumb'
import PlatformSelect from './components/PlatformSelect'

export default function App() {
  const [platform, setPlatform]         = useState(null)   // null = landing page
  const [meta, setMeta]                 = useState(null)
  const [topics, setTopics]             = useState([])
  const [currentTopic, setCurrentTopic] = useState(null)

  useEffect(() => {
    if (!platform) return
    setMeta(null)
    setTopics([])
    setCurrentTopic(null)
    const url = platform === 'bluesky' ? 'data/bluesky/topics.json' : 'data/topics.json'
    fetch(url).then(r => r.json()).then(json => {
      setTopics(json.topics)
      setMeta(json)
    })
  }, [platform])

  // ── Landing: platform selection ───────────────────────────────────────────
  if (!platform) {
    return (
      <>
        <Header />
        <div className="container">
          <PlatformSelect onSelect={setPlatform} />
        </div>
      </>
    )
  }

  // ── Topic detail ──────────────────────────────────────────────────────────
  if (currentTopic) {
    return (
      <>
        <Header />
        <div className="container">
          <Breadcrumb
            platform={platform}
            topic={currentTopic}
            onPlatform={() => { setPlatform(null); setCurrentTopic(null) }}
            onTopicList={() => setCurrentTopic(null)}
          />
          <DetailPanel topic={currentTopic} platform={platform} />
        </div>
      </>
    )
  }

  // ── Topic list ────────────────────────────────────────────────────────────
  return (
    <>
      <Header />
      <div className="container">
        <Breadcrumb
          platform={platform}
          topic={null}
          onPlatform={() => setPlatform(null)}
          onTopicList={null}
        />
        <MetaBar topics={topics} generated={meta?.generated} platform={platform} />
        <h2 className="section">Topics</h2>
        <TopicTable topics={topics} activeTopic={null} onSelect={setCurrentTopic} />
      </div>
    </>
  )
}
