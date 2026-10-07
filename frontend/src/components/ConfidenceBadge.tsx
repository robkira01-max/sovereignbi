import type { AskResponse } from '../api/client'

const COLORS: Record<string, string> = {
  'élevée': '#16a34a',
  'moyenne': '#d97706',
  'faible': '#dc2626',
}

interface Props {
  confidence: AskResponse['confidence']
}

export function ConfidenceBadge({ confidence }: Props) {
  if (!confidence) return null
  const color = COLORS[confidence.label] ?? '#6b7280'
  return (
    <span
      data-testid="confidence-badge"
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: '#fff',
        backgroundColor: color,
        marginLeft: '8px',
      }}
      title={confidence.explanation}
    >
      Confiance : {confidence.label} ({Math.round(confidence.score * 100)} %)
    </span>
  )
}
