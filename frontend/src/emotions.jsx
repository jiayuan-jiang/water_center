export const EMOTION_EMOJI = {
  neutral: '😐',
  fear: '😨',
  joy: '😊',
  surprise: '😲',
  sadness: '😢',
  anger: '😠',
  disgust: '🤢',
}

export function EmotionBadge({ emotion }) {
  if (!emotion) return null
  return (
    <span className="emotion-badge">
      {EMOTION_EMOJI[emotion] || ''} {emotion}
    </span>
  )
}
