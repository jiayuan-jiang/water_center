import { useState, useEffect, useMemo } from 'react'
import Header from './components/Header'
import MetaBar from './components/MetaBar'
import TopicTable from './components/TopicTable'
import DetailPanel from './components/DetailPanel'
import Breadcrumb from './components/Breadcrumb'
import PlatformSelect from './components/PlatformSelect'
import ModeSelect from './components/ModeSelect'
import OutlierTable from './components/OutlierTable'
import OutlierDetail from './components/OutlierDetail'
import NetworkGraph from './components/NetworkGraph'

function ViewTabs({ view, onChange }) {
  return (
    <div className="view-tabs">
      <button className={`view-tab${view === 'list' ? ' view-tab--active' : ''}`}
              onClick={() => onChange('list')}>List</button>
      <button className={`view-tab${view === 'network' ? ' view-tab--active' : ''}`}
              onClick={() => onChange('network')}>Similarity Network</button>
    </div>
  )
}

function detailUrl(platform, mode, id) {
  const url = new URL(window.location.href)
  url.search = new URLSearchParams({ platform, mode, item: String(id) }).toString()
  return url.toString()
}

export default function App() {
  const [platform, setPlatform]             = useState(null)   // null = landing page
  const [mode, setMode]                     = useState(null)   // null = mode selection
  const [view, setView]                     = useState('list') // 'list' | 'network'
  const [meta, setMeta]                     = useState(null)
  const [topics, setTopics]                 = useState([])
  const [currentTopic, setCurrentTopic]     = useState(null)
  const [outlierMeta, setOutlierMeta]       = useState(null)
  const [currentCluster, setCurrentCluster] = useState(null)
  const [network, setNetwork]               = useState(null)
  const [pendingItem, setPendingItem]       = useState(null)   // deep-linked item id awaiting its list to load

  const resetAll = () => {
    setPlatform(null)
    setMode(null)
    setView('list')
    setCurrentTopic(null)
    setCurrentCluster(null)
  }
  const backToMode = () => {
    setMode(null)
    setView('list')
    setCurrentTopic(null)
    setCurrentCluster(null)
  }

  useEffect(() => {
    if (!platform || mode !== 'topics') return
    setMeta(null)
    setTopics([])
    setCurrentTopic(null)
    const url = platform === 'reddit' ? 'data/topics.json' : `data/${platform}/topics.json`
    fetch(url).then(r => r.json()).then(json => {
      setTopics(json.topics)
      setMeta(json)
    })
  }, [platform, mode])

  useEffect(() => {
    if (!platform || mode !== 'outliers') return
    setOutlierMeta(null)
    setCurrentCluster(null)
    fetch(`data/outliers/${platform}/clusters.json`)
      .then(r => r.json())
      .then(setOutlierMeta)
      .catch(() => setOutlierMeta({ clusters: [] }))
  }, [platform, mode])

  useEffect(() => {
    setView('list')
  }, [platform, mode])

  useEffect(() => {
    if (!platform || !mode || mode === 'landing' || view !== 'network') return
    setNetwork(null)
    fetch(`data/network/${platform}/${mode}.json`)
      .then(r => r.ok ? r.json() : null)
      .then(setNetwork)
      .catch(() => setNetwork(null))
  }, [platform, mode, view])

  // ── Deep link: ?platform=bluesky&mode=outliers&item=28 opens straight to a node's detail ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const p = params.get('platform')
    const m = params.get('mode')
    const item = params.get('item')
    if (p && m) {
      setPlatform(p)
      setMode(m)
      setView('list')
      if (item) setPendingItem(item)
    }
  }, [])

  useEffect(() => {
    if (!pendingItem) return
    if (mode === 'topics' && topics.length) {
      const t = topics.find(x => String(x.id) === pendingItem)
      if (t) { setCurrentTopic(t); setPendingItem(null) }
    } else if (mode === 'outliers' && outlierMeta?.clusters?.length) {
      const c = outlierMeta.clusters.find(x => String(x.id) === pendingItem)
      if (c) { setCurrentCluster(c); setPendingItem(null) }
    }
  }, [pendingItem, mode, topics, outlierMeta])

  const steepById = useMemo(() => {
    const items = mode === 'topics' ? topics : (outlierMeta?.clusters ?? [])
    return new Map(items.map(item => [item.id, item.steep]))
  }, [mode, topics, outlierMeta])

  const openNetworkDetail = (node, { newTab } = {}) => {
    if (newTab) {
      window.open(detailUrl(platform, mode, node.id), '_blank', 'noopener')
      return
    }
    if (mode === 'topics') {
      const t = topics.find(x => x.id === node.id)
      if (t) setCurrentTopic(t)
    } else if (mode === 'outliers') {
      const c = outlierMeta?.clusters.find(x => x.id === node.id)
      if (c) setCurrentCluster(c)
    }
  }

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

  // ── Mode selection: topics or outliers ────────────────────────────────────
  if (!mode) {
    return (
      <>
        <Header />
        <div className="container">
          <Breadcrumb platform={platform} mode={null} current={null}
                      onPlatform={resetAll} />
          <ModeSelect platform={platform} onSelect={setMode} />
        </div>
      </>
    )
  }

  // ── Outlier flow ──────────────────────────────────────────────────────────
  if (mode === 'outliers') {
    if (currentCluster) {
      return (
        <>
          <Header />
          <div className="container">
            <Breadcrumb platform={platform} mode={mode} current={currentCluster.label}
                        onPlatform={resetAll} onMode={backToMode}
                        onList={() => setCurrentCluster(null)} />
            <OutlierDetail cluster={currentCluster} platform={platform} />
          </div>
        </>
      )
    }
    return (
      <>
        <Header />
        <div className="container">
          <Breadcrumb platform={platform} mode={mode} current={null}
                      onPlatform={resetAll} onMode={backToMode} />
          {outlierMeta ? (
            <>
              <p className="meta-bar">
                {outlierMeta.n_passing} unreviewed micro-clusters from{' '}
                {outlierMeta.n_outlier_docs?.toLocaleString()} unassigned docs ·
                ranked by novelty × recency · generated {outlierMeta.generated}
              </p>
              <h2 className="section">Outlier Signals</h2>
              <ViewTabs view={view} onChange={setView} />
              {view === 'network' ? (
                network ? (
                  <NetworkGraph data={network} onOpenDetail={openNetworkDetail} steepById={steepById} />
                ) : (
                  <p className="loading-state">Loading similarity network…</p>
                )
              ) : (
                <OutlierTable clusters={outlierMeta.clusters} onSelect={setCurrentCluster} />
              )}
            </>
          ) : (
            <p className="meta-bar">Loading outlier signals…</p>
          )}
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
          <Breadcrumb platform={platform} mode={mode} current={currentTopic.label}
                      onPlatform={resetAll} onMode={backToMode}
                      onList={() => setCurrentTopic(null)} />
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
        <Breadcrumb platform={platform} mode={mode} current={null}
                    onPlatform={resetAll} onMode={backToMode} />
        <MetaBar topics={topics} generated={meta?.generated} platform={platform} />
        <h2 className="section">Topics</h2>
        <ViewTabs view={view} onChange={setView} />
        {view === 'network' ? (
          network ? (
            <NetworkGraph data={network} onSelectNode={() => {}} steepById={steepById} />
          ) : (
            <p className="loading-state">Loading similarity network…</p>
          )
        ) : (
          <TopicTable topics={topics} activeTopic={null} onSelect={setCurrentTopic} />
        )}
      </div>
    </>
  )
}
