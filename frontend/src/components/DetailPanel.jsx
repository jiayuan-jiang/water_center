import { useState, useEffect, useRef, useCallback } from 'react'
import CommentCard from './CommentCard'
import TrendChart from './TrendChart'
import SubtopicPanel from './SubtopicPanel'
import EmotionPieChart from './EmotionPieChart'
import { SteepBadges } from '../steep'

export default function DetailPanel({ topic, platform }) {
  const [data, setData]                       = useState(null)
  const [trendData, setTrendData]             = useState(null)
  const [subtopicData, setSubtopicData]       = useState(null)
  const [activeSubtopic, setActiveSubtopic]   = useState(null)
  const [subtopicComments, setSubtopicComments] = useState(null)
  const [subtopicLoading, setSubtopicLoading] = useState(false)
  const commentListRef = useRef(null)

  useEffect(() => {
    setData(null)
    setSubtopicData(null)
    setActiveSubtopic(null)
    setSubtopicComments(null)
    const base = platform === 'bluesky' ? 'data/bluesky/topics' : 'data/topics'
    fetch(`${base}/t${topic.id}.json`)
      .then(r => r.json())
      .then(setData)
  }, [topic.id, platform])

  useEffect(() => {
    fetch(`data/subtopics/${platform}/t${topic.id}.json`)
      .then(r => r.ok ? r.json() : null)
      .then(setSubtopicData)
      .catch(() => setSubtopicData(null))
  }, [topic.id, platform])

  useEffect(() => {
    setTrendData(null)
    const file = platform === 'bluesky'
      ? 'data/bluesky_topic_trends.json'
      : 'data/reddit_topic_trends.json'
    fetch(file)
      .then(r => r.json())
      .then(setTrendData)
      .catch(() => {})
  }, [platform])

  const handleSubtopicSelect = useCallback((subtopicId) => {
    if (subtopicId === activeSubtopic) {
      setActiveSubtopic(null)
      setSubtopicComments(null)
      return
    }
    setActiveSubtopic(subtopicId)
    setSubtopicLoading(true)
    fetch(`data/subtopics/${platform}/t${topic.id}_s${subtopicId}.json`)
      .then(r => r.json())
      .then(d => { setSubtopicComments(d.comments); setSubtopicLoading(false) })
      .catch(() => setSubtopicLoading(false))
  }, [activeSubtopic, platform, topic.id])

  // Find which subtopic owns a given comment ID, then select it and scroll
  const handleCiteClick = useCallback((id) => {
    if (!subtopicData) return

    const ownerSubtopic = subtopicData.subtopics.find(st =>
      st.comment_ids.includes(id)
    )
    if (!ownerSubtopic) return

    const doScroll = () => {
      const el = document.getElementById(`comment-${id}`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }

    if (activeSubtopic === ownerSubtopic.subtopic_id) {
      doScroll()
    } else {
      setActiveSubtopic(ownerSubtopic.subtopic_id)
      setSubtopicLoading(true)
      fetch(`data/subtopics/${platform}/t${topic.id}_s${ownerSubtopic.subtopic_id}.json`)
        .then(r => r.json())
        .then(d => {
          setSubtopicComments(d.comments)
          setSubtopicLoading(false)
          // Wait for render then scroll
          setTimeout(doScroll, 80)
        })
        .catch(() => setSubtopicLoading(false))
    }
  }, [subtopicData, activeSubtopic, platform, topic.id])

  const citedIds = new Set(
    subtopicData?.subtopics.flatMap(st => st.key_quotes.map(q => q.id)) ?? []
  )

  const displayedComments = activeSubtopic !== null
    ? (subtopicComments ?? [])
    : (data?.comments ?? [])

  const unit = platform === 'bluesky' ? 'posts' : 'comments'

  return (
    <div id="detail">
      <div id="detail-header">
        <div>
          <h2>{topic.label}</h2>
          <SteepBadges steep={topic.steep} />
          <div className="detail-keywords">
            {topic.keywords.map(k => <span key={k} className="kw">{k}</span>)}
          </div>
          {topic.steep?.rationale && (
            <p className="steep-rationale steep-rationale--on-header">{topic.steep.rationale}</p>
          )}
        </div>
        <span className="detail-count">
          {data ? `${data.comments.length} representative ${unit} · sorted by score` : ''}
        </span>
      </div>

      <TrendChart trendData={trendData} topicId={topic.id} />

      <EmotionPieChart pct={data?.emotion?.pct} title="Emotion breakdown" />

      {subtopicData && (
        <SubtopicPanel
          subtopics={subtopicData.subtopics}
          active={activeSubtopic}
          onSelect={handleSubtopicSelect}
          onCiteClick={handleCiteClick}
        />
      )}

      <div className="comment-section-header">
        <span className="comment-section-title">Comments</span>
        {subtopicData && (
          <div className="subtopic-filter-bar">
            <button
              className={`filter-pill${activeSubtopic === null ? ' filter-pill--active' : ''}`}
              onClick={() => { setActiveSubtopic(null); setSubtopicComments(null) }}
            >
              All
            </button>
            {subtopicData.subtopics.map(st => (
              <button
                key={st.subtopic_id}
                className={`filter-pill${activeSubtopic === st.subtopic_id ? ' filter-pill--active' : ''}`}
                onClick={() => handleSubtopicSelect(st.subtopic_id)}
                title={st.label}
              >
                {st.label.length > 32 ? st.label.slice(0, 32) + '…' : st.label}
              </button>
            ))}
          </div>
        )}
      </div>

      <div id="comment-list" ref={commentListRef}>
        {subtopicLoading
          ? <div className="loading-state">Loading…</div>
          : !data && activeSubtopic === null
            ? <div className="loading-state">Loading…</div>
            : displayedComments.map(c => (
                <CommentCard
                  key={c.id}
                  comment={c}
                  platform={platform}
                  highlighted={citedIds.has(c.id)}
                />
              ))
        }
      </div>
    </div>
  )
}
