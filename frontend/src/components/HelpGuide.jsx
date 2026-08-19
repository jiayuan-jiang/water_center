import { useEffect } from 'react'
import { STEEP_CATEGORIES, STEEP_COLORS } from '../steep'
import EmotionPieChart from './EmotionPieChart'

const SAMPLE_EMOTION_PCT = {
  neutral: 41, anger: 22, joy: 10, fear: 10, sadness: 9, surprise: 5, disgust: 3,
}

function MoodVisual() {
  return (
    <div className="help-visual help-visual--mood">
      <EmotionPieChart pct={SAMPLE_EMOTION_PCT} />
      <p className="help-visual-caption">Example: emotion breakdown for one topic</p>
    </div>
  )
}

function ControversyVisual() {
  return (
    <div className="help-visual help-visual--controversy">
      <div className="help-controversy-row">
        <span className="help-controversy-tag">0.90 — Genuine debate</span>
        <div className="help-controversy-bar">
          <span className="help-controversy-fill help-controversy-fill--split" />
        </div>
      </div>
      <div className="help-controversy-row">
        <span className="help-controversy-tag">0.10 — One-sided</span>
        <div className="help-controversy-bar">
          <span className="help-controversy-fill help-controversy-fill--onesided" />
        </div>
      </div>
    </div>
  )
}

function SteepVisual() {
  return (
    <div className="help-visual help-visual--steep">
      {STEEP_CATEGORIES.map(cat => (
        <span key={cat} className="help-steep-chip">
          <span className="steep-dot" style={{ background: STEEP_COLORS[cat] }} />
          {cat}
        </span>
      ))}
    </div>
  )
}

function SubtopicVisual() {
  return (
    <div className="help-visual help-visual--subtopic">
      <p className="help-summary-example">
        Cottage owners describe rising algae bloom frequency as a new problem
        <button className="cite-link" type="button" tabIndex={-1}>[k2m9x1↗]</button>,
        while others push back that this is normal late-summer variation
        <button className="cite-link" type="button" tabIndex={-1}>[p7q4rz↗]</button>.
      </p>
      <blockquote className="subtopic-quote help-quote-example">
        <span className="quote-text">"never seen it this green in August before"</span>
        <span className="cite-link quote-cite">— k2m9x1↗</span>
      </blockquote>
    </div>
  )
}

function OutlierVisual() {
  const rows = [
    { label: 'Relevance', pct: 82 },
    { label: 'Novelty', pct: 65 },
    { label: 'Recency', pct: 90 },
  ]
  return (
    <div className="help-visual help-visual--controversy">
      {rows.map(r => (
        <div key={r.label} className="help-controversy-row">
          <span className="help-controversy-tag">{r.label}</span>
          <div className="help-controversy-bar">
            <span className="help-controversy-fill help-controversy-fill--split" style={{ width: `${r.pct}%` }} />
          </div>
        </div>
      ))}
    </div>
  )
}

function NetworkVisual() {
  const nodes = [
    { x: 60, y: 40, r: 16, tag: 'Environmental' },
    { x: 150, y: 30, r: 10, tag: 'Political' },
    { x: 130, y: 90, r: 13, tag: 'Environmental' },
    { x: 210, y: 80, r: 7, tag: 'Economic' },
  ]
  const edges = [[0, 1], [0, 2], [1, 2], [2, 3]]
  return (
    <svg className="help-visual help-visual--network" viewBox="0 0 260 120" width="100%" height="120">
      {edges.map(([a, b], i) => (
        <line key={i} x1={nodes[a].x} y1={nodes[a].y} x2={nodes[b].x} y2={nodes[b].y}
              stroke="var(--border)" strokeWidth="1.5" />
      ))}
      {nodes.map((n, i) => (
        <circle key={i} cx={n.x} cy={n.y} r={n.r}
                fill="var(--kw-bg)" stroke={STEEP_COLORS[n.tag]} strokeWidth="2.5" />
      ))}
    </svg>
  )
}

const SECTIONS = [
  {
    title: 'Mood',
    visual: MoodVisual,
    body: (
      <>
        <p>Every comment or post is automatically read and tagged with its overall
        tone (positive / neutral / negative) and its dominant emotion — joy, anger,
        fear, sadness, disgust, or surprise.</p>
        <p>You'll see the dominant emotion as a badge in the <b>Mood</b> column, and
        a full breakdown as a pie chart on each topic's detail page.</p>
        <p><b>Why it matters:</b> it's a fast way to gauge the public's emotional
        temperature on a topic before reading through individual comments.</p>
      </>
    ),
  },
  {
    title: 'Controversy',
    visual: ControversyVisual,
    body: (
      <>
        <p>A score from 0 to 1 estimating how <i>split</i> opinion is on a topic —
        not just whether it's negative, but whether people are actually disagreeing
        with each other.</p>
        <p>An AI reads a sample of the real comments and checks for genuine
        back-and-forth debate versus everyone saying the same thing. A topic that's
        universally described as bad (e.g. contamination) scores <i>low</i> — that's
        "one-sided," not controversial — while a topic people are actively arguing
        about (e.g. a policy proposal) scores <i>high</i>.</p>
        <p><b>Why an AI reads it instead of a formula:</b> simple math (like the
        ratio of positive to negative comments) is easy to fool — a topic where
        everyone agrees the problem is bad just looks "50/50" on paper if people
        phrase it in mixed positive/negative language, while a topic where people
        are genuinely arguing over who's at fault can look one-sided if both sides
        use negative words. Having the AI actually read the comments and judge
        whether there's a substantiated disagreement, not just count words, matched
        manual human review far better than any formula tried.</p>
        <p><b>Why it matters:</b> a one-sided problem and an actively contested one
        need very different kinds of engagement.</p>
      </>
    ),
  },
  {
    title: 'STEEP',
    visual: SteepVisual,
    body: (
      <>
        <p>A standard horizon-scanning framework: every topic is tagged with which
        kind of driver is behind it — <b>S</b>ocial, <b>T</b>echnological,
        <b> E</b>conomic, <b>E</b>nvironmental, and/or <b>P</b>olitical. A topic can
        carry more than one tag.</p>
        <p>Shown as colored dot badges next to each topic, as a filter bar you can
        click to narrow the list to one category, and as the ring color around
        nodes in the Similarity Network.</p>
        <p><b>Why it matters:</b> lets you quickly filter down to just the kind of
        signal you're reviewing — e.g. only Political-tagged issues.</p>
      </>
    ),
  },
  {
    title: 'Similarity Network',
    visual: NetworkVisual,
    body: (
      <>
        <p>A map of how closely related each topic (or unlabeled micro-cluster) is
        to the others, based on what people actually wrote — not just shared
        keywords.</p>
        <p>Each circle is a topic; a bigger circle means more posts. Two topics
        connected by a line are being discussed in similar ways. The slider lets you
        raise the bar so only the strongest connections show.</p>
        <p><b>Why it matters:</b> reveals clusters of related concerns that don't
        share a label but are effectively part of the same conversation.</p>
      </>
    ),
  },
  {
    title: 'Sub-topics & Grounded Summaries',
    visual: SubtopicVisual,
    body: (
      <>
        <p>Inside each topic, comments are further split into smaller sub-topics
        so you're not stuck reading hundreds of comments to find one thread of
        conversation.</p>
        <p>Each sub-topic gets a short AI-written summary — but a <b>grounded</b>{' '}
        one: every sentence must cite the specific comment(s) it's based on (the
        clickable <code>[id↗]</code> tags), and every quoted phrase is copied
        verbatim from a real comment, never invented. Click any citation to jump
        straight to that comment.</p>
        <p><b>Why it matters:</b> you can check every claim in the summary against
        the actual source text, instead of trusting an AI-written summary blind —
        a normal risk with AI summaries that this is built to avoid.</p>
      </>
    ),
  },
  {
    title: 'Outlier Signals',
    visual: OutlierVisual,
    body: (
      <>
        <p>Topic modeling can't confidently place every comment into one of the
        labeled Topics — around 40% are left unassigned. <b>Outlier Signals</b>{' '}
        re-groups those into small micro-clusters, so early or emerging issues
        that haven't earned their own topic yet don't just get thrown away.</p>
        <p>Each micro-cluster is scored on three things: <b>Relevance</b> (is
        this actually about the Great Lakes, not off-topic noise), <b>Novelty</b>{' '}
        (how different is it from every existing labeled topic — is it genuinely
        something new), and <b>Recency</b> (is this a recent, growing conversation
        rather than old chatter). Clusters are ranked by novelty × recency among
        the ones that clear the relevance bar.</p>
        <p><b>Why it matters:</b> unlike the curated Topics list, these are{' '}
        <i>unreviewed candidates</i> — a shortlist for a human reviewer to triage
        into real emerging issues versus noise, not a finished narrative.</p>
      </>
    ),
  },
]

export default function HelpGuide({ onClose }) {
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="help-overlay" onClick={onClose}>
      <div className="help-modal" onClick={e => e.stopPropagation()}>
        <div className="help-modal-header">
          <div>
            <h2>How to read this</h2>
            <p>Four automated signals layered on top of every topic and micro-cluster</p>
          </div>
          <button className="help-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="help-modal-body">
          {SECTIONS.map(({ title, visual: Visual, body }) => (
            <section key={title} className="help-section">
              <h3>{title}</h3>
              <Visual />
              {body}
            </section>
          ))}
        </div>
      </div>
    </div>
  )
}
