import { useState } from 'react'
import HelpGuide from './HelpGuide'

export default function Header() {
  const [showHelp, setShowHelp] = useState(false)
  return (
    <header>
      <div className="header-row">
        <div>
          <h1>Great Lakes Horizon Scan — Topic Browser</h1>
          <p>Social media topic analysis · BERTopic · 2023–2026</p>
        </div>
        <button className="help-btn" onClick={() => setShowHelp(true)}>
          <span className="help-btn-icon">?</span> How to read this
        </button>
      </div>
      {showHelp && <HelpGuide onClose={() => setShowHelp(false)} />}
    </header>
  )
}
