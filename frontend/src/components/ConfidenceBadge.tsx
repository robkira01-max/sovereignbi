import type { AskResponse } from '../api/client'
import { useLocale } from '../hooks/useLocale'

const COLORS: Record<string, string> = {
  'élevée': '#16a34a',
  'moyenne': '#d97706',
  'faible': '#dc2626',
}

const CONFIDENCE_KEY: Record<string, string> = {
  'élevée': 'confidence.high',
  'moyenne': 'confidence.medium',
  'faible': 'confidence.low',
}

interface Props {
  confidence: AskResponse['confidence']
}

export function ConfidenceBadge({ confidence }: Props) {
  const { t } = useLocale()
  if (!confidence) return null
  const color = COLORS[confidence.label] ?? '#6b7280'
  const labelKey = CONFIDENCE_KEY[confidence.label]
  const translatedLabel = labelKey ? t(labelKey) : confidence.label
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
        marginInlineStart: '8px',
      }}
      title={confidence.explanation}
    >
      {t('confidence.label')} {translatedLabel} ({Math.round(confidence.score * 100)} %)
    </span>
  )
}
