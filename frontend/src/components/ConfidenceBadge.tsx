import type { AskResponse } from '../api/client'
import { useLocale } from '../hooks/useLocale'

const BG: Record<string, string> = {
  'élevée': 'oklch(92% 0.06 145)',
  'moyenne': 'oklch(95% 0.06 75)',
  'faible':  'oklch(94% 0.06 25)',
}

const FG: Record<string, string> = {
  'élevée': 'var(--success)',
  'moyenne': 'oklch(42% 0.16 75)',
  'faible':  'var(--danger)',
}

const CONFIDENCE_KEY: Record<string, string> = {
  'élevée': 'confidence.high',
  'moyenne': 'confidence.medium',
  'faible':  'confidence.low',
}

interface Props {
  confidence: AskResponse['confidence']
}

export function ConfidenceBadge({ confidence }: Props) {
  const { t } = useLocale()
  if (!confidence) return null
  const bg = BG[confidence.label] ?? 'oklch(93% 0.01 220)'
  const fg = FG[confidence.label] ?? 'var(--muted)'
  const labelKey = CONFIDENCE_KEY[confidence.label]
  const translatedLabel = labelKey ? t(labelKey) : confidence.label
  return (
    <span
      data-testid="confidence-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 10px',
        borderRadius: '999px',
        fontSize: '0.75rem',
        fontWeight: 600,
        color: fg,
        backgroundColor: bg,
        marginInlineStart: '8px',
      }}
      title={confidence.explanation}
    >
      {t('confidence.label')} {translatedLabel} ({Math.round(confidence.score * 100)} %)
    </span>
  )
}
